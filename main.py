import requests
import time
import logging
from datetime import datetime, timezone
from binance.client import Client
from binance.enums import *
import telegram

# ===== CONFIG =====
API_KEY = "YOUR_TESTNET_API_KEY"
API_SECRET = "YOUR_TESTNET_API_SECRET"

TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

EQUITY = 118.0          # starting USDT
ALLOC_PCT = 0.05        # 5% per trade
LEVERAGE = 5            # 5x leverage
TP_PCT = 0.007          # Take Profit 0.7%
SL_PCT = 0.007          # Stop Loss 0.7%
MAX_TRADES = 3

# ===== API SETUP (TESTNET) =====
client = Client(API_KEY, API_SECRET, testnet=True)
TREND_API = "https://api.coingecko.com/api/v3/search/trending"

# ===== TELEGRAM BOT =====
tg_bot = telegram.Bot(token=TELEGRAM_TOKEN)

# ===== LOGGING =====
logging.basicConfig(format="%(asctime)s, %(levelname)s: %(message)s", level=logging.INFO)

# ===== TRADE TRACKER =====
open_trades = {}
trade_history = []
daily_pnl = 0.0
daily_start_equity = EQUITY
last_summary_date = datetime.now(timezone.utc).date()

# ===== FUNCTIONS =====
def send_telegram(msg):
    try:
        tg_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")

def record_trade(symbol, entry, exit, qty, pnl):
    global daily_pnl
    trade_history.append({
        "symbol": symbol,
        "entry": entry,
        "exit": exit,
        "qty": qty,
        "pnl": pnl,
        "time": datetime.now(timezone.utc).isoformat()
    })
    daily_pnl += pnl

def print_daily_summary():
    global daily_pnl, daily_start_equity, last_summary_date, EQUITY
    wins = sum(1 for t in trade_history if t["pnl"] > 0)
    losses = sum(1 for t in trade_history if t["pnl"] <= 0)
    trades = len(trade_history)
    net_pnl = round(daily_pnl, 4)
    pct = round((net_pnl / daily_start_equity) * 100, 2) if daily_start_equity else 0

    summary = f"--- DAILY SUMMARY ({last_summary_date}) ---\n"
    summary += f"Total Trades: {trades} | Wins: {wins} | Losses: {losses}\n"
    summary += f"Net PnL: {net_pnl} USDT ({pct}%) | Equity: {round(daily_start_equity + net_pnl, 4)} USDT\n"
    summary += "----------------------------------------"

    logging.info(summary)
    send_telegram(summary)

    trade_history.clear()
    daily_start_equity += net_pnl
    EQUITY = daily_start_equity
    daily_pnl = 0.0
    last_summary_date = datetime.now(timezone.utc).date()

def get_binance_symbols():
    try:
        info = client.get_exchange_info()
        return {s["symbol"] for s in info["symbols"]}
    except Exception as e:
        logging.error(f"Failed to fetch Binance symbols: {e}")
        return set()

def fetch_trending_binance_tokens(binance_symbols):
    try:
        r = requests.get(TREND_API, timeout=10)
        data = r.json().get("coins", [])
        trending = [coin["item"]["symbol"].upper() + "USDT" for coin in data]
        valid = [t for t in trending if t in binance_symbols]
        return valid[:MAX_TRADES] if valid else ["BTCUSDT"]
    except Exception as e:
        logging.error(f"Failed to fetch trending tokens: {e}")
        return ["BTCUSDT"]

# ===== MAIN LOOP =====
def run_bot():
    global EQUITY, last_summary_date
    logging.info(f"🚀 Starting Binance Testnet Scalper (EQUITY={EQUITY} USDT, LEVERAGE={LEVERAGE}x)")

    binance_symbols = get_binance_symbols()
    if not binance_symbols:
        logging.error("No Binance symbols found. Exiting.")
        return

    try:
        while True:
            trending = fetch_trending_binance_tokens(binance_symbols)
            if not trending:
                time.sleep(10)
                continue

            # Check trades to close
            to_close = []
            for sym, trade in open_trades.items():
                try:
                    ticker = client.get_symbol_ticker(symbol=sym)
                    price = float(ticker["price"])
                except Exception:
                    continue

                if price >= trade["tp"]:
                    logging.info(f"✅ SELL (TP) → {sym} @ {price}")
                    pnl = (price - trade["entry"]) * trade["qty"]
                    record_trade(sym, trade["entry"], price, trade["qty"], pnl)
                    EQUITY += pnl
                    send_telegram(f"✅ SELL (TP) → {sym} @ {price} | PnL: {round(pnl,4)} USDT")
                    to_close.append(sym)
                elif price <= trade["sl"]:
                    logging.info(f"❌ SELL (SL) → {sym} @ {price}")
                    pnl = (price - trade["entry"]) * trade["qty"]
                    record_trade(sym, trade["entry"], price, trade["qty"], pnl)
                    EQUITY += pnl
                    send_telegram(f"❌ SELL (SL) → {sym} @ {price} | PnL: {round(pnl,4)} USDT")
                    to_close.append(sym)

            for sym in to_close:
                open_trades.pop(sym, None)

            # Open new trades
            for sym in trending:
                if len(open_trades) >= MAX_TRADES:
                    break
                if sym not in open_trades:
                    try:
                        ticker = client.get_symbol_ticker(symbol=sym)
                        price = float(ticker["price"])
                    except Exception as e:
                        logging.warning(f"Symbol {sym} not tradable: {e}")
                        continue

                    alloc = EQUITY * ALLOC_PCT * LEVERAGE
                    qty = round(alloc / price, 6)
                    tp = price * (1 + TP_PCT)
                    sl = price * (1 - SL_PCT)

                    open_trades[sym] = {"entry": price, "tp": tp, "sl": sl, "qty": qty}
                    logging.info(f"✅ BUY → {sym} @ {price} | qty={qty} | TP={tp:.2f}, SL={sl:.2f}")
                    send_telegram(f"✅ BUY → {sym} @ {price} | qty={qty} | TP={tp:.2f}, SL={sl:.2f}")

            logging.info(f"Open trades: {list(open_trades.keys())}")

            # Daily summary
            if datetime.now(timezone.utc).date() != last_summary_date:
                print_daily_summary()

            time.sleep(10)

    except KeyboardInterrupt:
        logging.info("Bot stopped manually. Printing final summary...")
        print_daily_summary()

# ===== RUN =====
if __name__ == "__main__":
    run_bot()
        
