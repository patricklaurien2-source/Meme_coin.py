
import os
import time
import logging
import requests

from datetime import datetime, timezone

# ==========================================
# IKKEZ77 BOT 2.0
# EARLY COIN DISCOVERY
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

GECKO_URL = (
    "https://api.geckoterminal.com/api/v2/"
    "networks/solana/new_pools"
)

HEADERS = {
    "Accept": "application/json;version=20230302"
}

# Daten
OPEN_TRADES = {}
TRACKED_TOKENS = set()
TRACKED_POOLS = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(BOT_NAME)


def parse_creation_time(value):
    """Liest das Erstellungsdatum eines Pools."""

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def get_pool_age_minutes(created_at):
    """Berechnet das Alter eines Pools."""

    creation_time = parse_creation_time(created_at)

    if creation_time is None:
        return None

    now = datetime.now(timezone.utc)

    age = now - creation_time

    return age.total_seconds() / 60


def get_new_pools():
    """Lädt neue Solana-Pools von GeckoTerminal."""

    params = {
        "page": 1,
        "include": "base_token"
    }

    try:
        response = requests.get(
            GECKO_URL,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        if response.status_code == 429:
            logger.warning(
                "GeckoTerminal Rate Limit erreicht."
            )
            return []

        response.raise_for_status()

        result = response.json()

        return result.get("data", [])

    except requests.RequestException as error:
        logger.error(
            "GeckoTerminal Verbindungsfehler: %s",
            error
        )
        return []

    except ValueError:
        logger.error(
            "GeckoTerminal Antwort konnte nicht gelesen werden."
        )
        return []


def extract_token_address(pool):
    """Liest die Basis-Token-Adresse aus."""

    relationships = pool.get("relationships", {})

    base_token = relationships.get(
        "base_token", {}
    )

    token_data = base_token.get("data", {})

    token_id = token_data.get("id", "")

    if token_id.startswith("solana_"):
        return token_id[len("solana_"):]

    return ""


def discover_fresh_coins():
    """Findet Pools, die höchstens 60 Minuten alt sind."""

    pools = get_new_pools()

    fresh_coins = []

    logger.info(
        "GeckoTerminal: %s Pools empfangen.",
        len(pools)
    )

    for pool in pools:

        attributes = pool.get("attributes", {})

        pool_address = attributes.get("address", "")

        created_at = attributes.get(
            "pool_created_at"
        )

        if not pool_address:
            continue

        if pool_address in TRACKED_POOLS:
            continue

        age_minutes = get_pool_age_minutes(
            created_at
        )

        # Ohne gültiges Erstellungsdatum keine Freigabe.
        if age_minutes is None:
            logger.warning(
                "Pool ohne gültiges Erstellungsdatum übersprungen: %s",
                pool_address
            )
            continue

        if age_minutes < 0:
            continue

        if age_minutes > MAX_POOL_AGE_MINUTES:
            continue

        token_address = extract_token_address(pool)

        if not token_address:
            logger.warning(
                "Keine Token-Adresse gefunden: %s",
                pool_address
            )
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

        logger.info(
            "NEUER COIN | %s | Alter: %.1f Minuten | "
            "Liquidität: $%.2f | Token: %s",
            coin["pool_name"],
            coin["age_minutes"],
            coin["liquidity_usd"],
            coin["token_address"]
        )

    logger.info(
        "Neue Coins unter 60 Minuten: %s",
        len(fresh_coins)
    )

    return fresh_coins


def scan_once():
    """Ein Erkennungsdurchlauf."""

    logger.info("Starte Early-Coin-Suche ...")

    coins = discover_fresh_coins()

    logger.info(
        "Erkennungsdurchlauf abgeschlossen. Kandidaten: %s",
        len(coins)
    )

    return coins


def start_bot():

    logger.info("=" * 45)
    logger.info("%s gestartet", BOT_NAME)

    mode = (
        TRADING_MODE
        if TRADING_MODE in ("paper", "real")
        else "paper"
    )

    logger.info("Modus: %s", mode.upper())
    logger.info("Einsatz pro Kauf: $%.2f", TRADE_SIZE_USD)
    logger.info("Max. Positionen: %s", MAX_OPEN_POSITIONS)
    logger.info("Take Profit: +%.0f%%", TAKE_PROFIT_PERCENT)
    logger.info("Stop Loss: %.0f%%", STOP_LOSS_PERCENT)

    logger.info(
        "Maximales Pool-Alter: %s Minuten",
        MAX_POOL_AGE_MINUTES
    )

    logger.info("Käufe sind noch nicht aktiviert.")
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
