import os
import time
import logging

# ==================================
# IKKEZ77 BOT 2.0
# ==================================

BOT_NAME = "ikkez77 Bot 2.0"

TRADING_MODE = os.getenv("TRADING_MODE", "paper").lower()

# REAL bleibt zunächst gesperrt
LIVE_TRADING_ENABLED = False

# Handelsregeln
TRADE_SIZE_USD = 1.00
MAX_OPEN_POSITIONS = 5

TAKE_PROFIT_PERCENT = 200.0
STOP_LOSS_PERCENT = -30.0

# Daten
OPEN_TRADES = {}
TRACKED_TOKENS = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def start_bot():
    logging.info("=" * 40)
    logging.info("%s gestartet", BOT_NAME)
    logging.info("Modus: %s", TRADING_MODE.upper())
    logging.info("Einsatz: $%.2f", TRADE_SIZE_USD)
    logging.info("Max. Positionen: %s", MAX_OPEN_POSITIONS)
    logging.info("Take Profit: +%.0f%%", TAKE_PROFIT_PERCENT)
    logging.info("Stop Loss: %.0f%%", STOP_LOSS_PERCENT)
    logging.info("Echtgeldhandel ist noch gesperrt.")
    logging.info("=" * 40)

if __name__ == "__main__":
    start_bot()
