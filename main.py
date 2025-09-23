import requests
import time
import logging
import pandas as pd
from datetime import datetime

# ===== CONFIG =====
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SIGNUSDT", "HEMIUSDT", "AVNTUSDT", "0GUSDT", "PENGUUSDT", "LINEAUSDT"]
EQUITY = 118.0
ALLOC_PCT = 0.05
LEVERAGE = 5
TP_PCT = 0.007
SL_PCT = 0.007
MAX_TRADES = 6
INTERVAL = "1m"
LOG_FILE = "bot_logs.txt"

# ===== LOGGING =====
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

# ===== HELPER FUNCTIONS =====
def fetch_klines(symbol, interval="1m", limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume',
                                         'close_time','qav','count','taker_base','taker_quote','ignore'])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta>0,0)).rolling(period).mean()
    loss = (-delta.where(delta<0,0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_trend(symbol):
    df = fetch_klines(symbol, INTERVAL)
    if df is None or len(df) < 200:
        return False
    df['ema50'] = ema(df['close'],50)
    df['ema200'] = ema(df['close'],200)
    df['rsi'] = rsi(df['close'])
    last = df.iloc[-1]
    if last['ema50'] > last['ema200'] and last['rsi'] < 70:
        return True
    return False

def fetch_price(symbol):
    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        r = requests.get(url, params={"symbol": symbol}, timeout=5)
        return float(r.json()["price"])
    except:
        return None

def simulate_trade(symbol, equity):
    price = fetch_price(symbol)
    if price is None:
        return None
    alloc = equity * ALLOC_PCT * LEVERAGE
    qty = alloc / price
    tp = price * (1 + TP_PCT)
    sl = price * (1 - SL_PCT)
    logging.info(f"DRY BUY → {symbol} @ {price:.5f} | qty={qty:.4f} | TP={tp:.5f} | SL={sl:.5f}")
    return {"symbol": symbol, "entry": price, "tp": tp, "sl": sl, "qty": qty}

# ===== MAIN LOOP =====
def run_bot():
    logging.info(f"Starting Binance Trend Scalper DRY-RUN (EQUITY={EQUITY} USDT, LEVERAGE={LEVERAGE}x)")
    open_trades = []
    equity = EQUITY

    while True:
        for symbol in SYMBOLS:
            try:
                if check_trend(symbol):
                    if len(open_trades) < MAX_TRADES:
                        trade = simulate_trade(symbol, equity)
                        if trade:
                            open_trades.append(trade)
                else:
                    logging.info(f"❌ Skip {symbol} (Downtrend / Overbought)")
            except Exception as e:
                logging.error(f"{symbol} error: {e}")

        logging.info(f"Open simulated trades: {len(open_trades)} -> {[t['symbol'] for t in open_trades]}")
        time.sleep(10)

if __name__ == "__main__":
    run_bot()
    
