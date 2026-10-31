
import os
import time
import logging
import requests

from datetime import datetime, timezone

# ==========================================
# IKKEZ77 BOT 2.0
# EARLY COIN HUNTER
# ==========================================

BOT_NAME = "ikkez77 Bot 2.0"

TRADING_MODE = os.getenv(
    "TRADING_MODE", "paper"
).strip().lower()

LIVE_TRADING_ENABLED = os.getenv(
    "LIVE_TRADING_ENABLED", "false"
).strip().lower() in ("1", "true", "yes", "on")

# Handelsregeln
TRADE_SIZE_USD = 1.00
MAX_OPEN_POSITIONS = 5
TAKE_PROFIT_PERCENT = 200.0
STOP_LOSS_PERCENT = -30.0

# Coin-Erkennung
SCAN_INTERVAL_SECONDS = 60
MAX_POOL_AGE_MINUTES = 60

# Sicherheitsprüfung
MAX_RUGCHECK_SCORE = 20
RUGCHECK_CACHE_SECONDS = 600

GECKO_URL = (
    "https://api.geckoterminal.com/api/v2/"
    "networks/solana/new_pools"
)

RUGCHECK_URL = (
    "https://api.rugcheck.xyz/v1/tokens/"
)

HEADERS = {
    "Accept": "application/json"
}

# Daten
OPEN_TRADES = {}
TRACKED_TOKENS = set()
TRACKED_POOLS = set()
RUGCHECK_CACHE = {}

session = requests.Session()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(BOT_NAME)


def parse_creation_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def get_pool_age_minutes(created_at):
    creation_time = parse_creation_time(created_at)

    if creation_time is None:
        return None

    now = datetime.now(timezone.utc)

    return (
        now - creation_time
    ).total_seconds() / 60


def get_new_pools():
    params = {
        "page": 1,
        "include": "base_token"
    }

    try:
        response = session.get(
            GECKO_URL,
            headers={
                "Accept": "application/json;version=20230302"
            },
            params=params,
            timeout=15
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            logger.error("Ungültige GeckoTerminal-Antwort.")
            return []

        return result.get("data", [])

    except requests.RequestException as error:
        logger.error(
            "GeckoTerminal Fehler: %s",
            error
        )
        return []

    except ValueError:
        logger.error(
            "GeckoTerminal JSON konnte nicht gelesen werden."
        )
        return []


def extract_token_address(pool):
    relationships = pool.get("relationships", {})

    base_token = relationships.get(
        "base_token", {}
    )

    token_data = base_token.get("data", {})

    token_id = token_data.get("id", "")

    if token_id.startswith("solana_"):
        return token_id[len("solana_"):]

    return ""


def check_rugcheck(token_address):
    """
    Prüft einen Token bei RugCheck.

    Bei API-Fehlern oder fehlenden Daten:
    keine Sicherheitsfreigabe.
    """

    now = time.time()

    cached = RUGCHECK_CACHE.get(token_address)

    if cached:
        cache_age = now - cached["timestamp"]

        if cache_age < RUGCHECK_CACHE_SECONDS:
            return cached["result"]

    url = (
        RUGCHECK_URL
        + token_address
        + "/report/summary"
    )

    try:
        response = session.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code == 404:
            logger.warning(
                "RugCheck kennt Token noch nicht: %s",
                token_address
            )
            return {
                "approved": False,
                "reason": "Kein RugCheck-Bericht vorhanden"
            }

        if response.status_code == 429:
            logger.warning(
                "RugCheck Rate Limit erreicht."
            )
            return {
                "approved": False,
                "reason": "RugCheck Rate Limit"
            }

        response.raise_for_status()

        report = response.json()

        if not isinstance(report, dict):
            return {
                "approved": False,
                "reason": "Ungültige RugCheck-Antwort"
            }

        normalized_score = report.get(
            "score_normalised"
        )

        risks = report.get("risks")

        if normalized_score is None or not isinstance(
            risks, list
        ):
            return {
                "approved": False,
                "reason": "RugCheck-Daten unvollständig"
            }

        normalized_score = int(normalized_score)

        dangerous_levels = {
            "danger",
            "critical",
            "high"
        }

        dangerous_risks = []

        for risk in risks:
            if not isinstance(risk, dict):
                continue

            level = str(
                risk.get("level", "")
            ).lower()

            if level in dangerous_levels:
                dangerous_risks.append(
                    risk.get("name", "Unbekanntes Risiko")
                )

        if dangerous_risks:
            result = {
                "approved": False,
                "score": normalized_score,
                "reason": (
                    "Gefährliche Risiken: "
                    + ", ".join(dangerous_risks)
                )
            }

        elif normalized_score > MAX_RUGCHECK_SCORE:
            result = {
                "approved": False,
                "score": normalized_score,
                "reason": "RugCheck-Risikoscore zu hoch"
            }

        else:
            result = {
                "approved": True,
                "score": normalized_score,
                "reason": "RugCheck-Prüfung bestanden"
            }

        RUGCHECK_CACHE[token_address] = {
            "timestamp": now,
            "result": result
        }

        return result

    except requests.RequestException as error:
        logger.error(
            "RugCheck Verbindungsfehler: %s",
            error
        )

        return {
            "approved": False,
            "reason": "RugCheck nicht erreichbar"
        }

    except (ValueError, TypeError):
        logger.error(
            "RugCheck-Antwort konnte nicht verarbeitet werden."
        )

        return {
            "approved": False,
            "reason": "Ungültige RugCheck-Daten"
        }


def discover_fresh_coins():
    pools = get_new_pools()

    fresh_coins = []

    logger.info(
        "GeckoTerminal: %s Pools empfangen.",
        len(pools)
    )

    for pool in pools:

        attributes = pool.get("attributes", {})

        pool_address = attributes.get("address", "")

        if not pool_address:
            continue

        if pool_address in TRACKED_POOLS:
            continue

        created_at = attributes.get(
            "pool_created_at"
        )

        age_minutes = get_pool_age_minutes(
            created_at
        )

        if age_minutes is None:
            continue

        if age_minutes < 0:
            continue

        if age_minutes > MAX_POOL_AGE_MINUTES:
            continue

        token_address = extract_token_address(pool)

        if not token_address:
            continue

        TRACKED_POOLS.add(pool_address)
        TRACKED_TOKENS.add(token_address)

        coin = {
            "pool_address": pool_address,
            "token_address": token_address,
            "pool_name": attributes.get(
                "name", "Unbekannt"
            ),
            "created_at": created_at,
            "age_minutes": round(age_minutes, 2),
            "liquidity_usd": float(
                attributes.get("reserve_in_usd") or 0
            )
        }

        fresh_coins.append(coin)

    return fresh_coins


def scan_once():
    logger.info("Starte Early-Coin-Suche ...")

    coins = discover_fresh_coins()

    logger.info(
        "Neue Pools unter 60 Minuten: %s",
        len(coins)
    )

    approved_coins = []

    for coin in coins:

        logger.info(
            "Prüfe Sicherheit: %s",
            coin["pool_name"]
        )

        security = check_rugcheck(
            coin["token_address"]
        )

        if not security["approved"]:
            logger.warning(
                "ABGELEHNT | %s | %s",
                coin["pool_name"],
                security["reason"]
            )
            continue

        coin["rugcheck_score"] = security["score"]

        approved_coins.append(coin)

        logger.info(
            "SICHERHEIT BESTANDEN | %s | "
            "RugCheck-Risiko: %s",
            coin["pool_name"],
            security["score"]
        )

    logger.info(
        "Sicherheitsprüfung bestanden: %s von %s",
        len(approved_coins),
        len(coins)
    )

    return approved_coins


def start_bot():

    mode = (
        TRADING_MODE
        if TRADING_MODE in ("paper", "real")
        else "paper"
    )

    logger.info("=" * 45)
    logger.info("%s gestartet", BOT_NAME)
    logger.info("Modus: %s", mode.upper())
    logger.info("Einsatz pro Kauf: $%.2f", TRADE_SIZE_USD)
    logger.info("Max. Positionen: %s", MAX_OPEN_POSITIONS)
    logger.info("Take Profit: +%.0f%%", TAKE_PROFIT_PERCENT)
    logger.info("Stop Loss: %.0f%%", STOP_LOSS_PERCENT)
    logger.info("Max. Pool-Alter: %s Minuten", MAX_POOL_AGE_MINUTES)
    logger.info("Max. RugCheck-Risikoscore: %s", MAX_RUGCHECK_SCORE)
    logger.info("Automatische Käufe sind noch deaktiviert.")
    logger.info("=" * 45)

    while True:

        try:
            scan_once()

        except Exception:
            logger.exception(
                "Unerwarteter Fehler beim Scan."
            )

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    start_bot()
