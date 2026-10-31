
import os
import time
import logging

# ==========================================
# IKKEZ77 BOT 2.0
# Neue Solana-Memecoin-Bot-Basis
# ==========================================

BOT_NAME = "ikkez77 Bot 2.0"

# Handelsmodus: PAPER ist der Standard
TRADING_MODE = os.getenv(
    "TRADING_MODE", "paper"
).strip().lower()

# REAL kann später über Render aktiviert werden
LIVE_TRADING_ENABLED = os.getenv(
    "LIVE_TRADING_ENABLED", "false"
).strip().lower() in ("1", "true", "yes", "on")

# Handelsregeln
TRADE_SIZE_USD = 1.00
MAX_OPEN_POSITIONS = 5

TAKE_PROFIT_PERCENT = 200.0
STOP_LOSS_PERCENT = -30.0

# Daten
OPEN_TRADES = {}
TRACKED_TOKENS = set()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def start_bot():
    logging.info("=" * 45)
    logging.info("%s gestartet", BOT_NAME)

    if TRADING_MODE not in ("paper", "real"):
        logging.warning(
            "Unbekannter Handelsmodus: %s. PAPER wird verwendet.",
            TRADING_MODE
        )
        mode = "paper"
    else:
        mode = TRADING_MODE

    logging.info("Modus: %s", mode.upper())
    logging.info("Einsatz pro Kauf: $%.2f", TRADE_SIZE_USD)
    logging.info("Maximale offene Positionen: %s", MAX_OPEN_POSITIONS)
    logging.info("Take Profit: +%.0f%%", TAKE_PROFIT_PERCENT)
    logging.info("Stop Loss: %.0f%%", STOP_LOSS_PERCENT)
    logging.info(
        "REAL-Freigabe konfiguriert: %s",
        LIVE_TRADING_ENABLED
    )

    if mode == "real":
        if LIVE_TRADING_ENABLED:
            logging.warning(
                "REAL-Modus ausgewählt. Die echte Swap-Ausführung "
                "muss noch implementiert und getestet werden."
            )
        else:
            logging.warning(
                "REAL-Modus ausgewählt, aber LIVE_TRADING_ENABLED "
                "ist nicht aktiviert."
            )

    logging.info("Bot-Grundsystem erfolgreich gestartet.")
    logging.info("=" * 45)


if __name__ == "__main__":
    start_bot()
