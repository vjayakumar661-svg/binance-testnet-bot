import pandas as pd
import time
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# ===== CONFIG =====
API_KEY = "RNHRocFsqfkAXQPX9iJgeIna24lL5HHbsM3vo5t8MFEoQ8KuYvuD7QgxSWQ8HW0r"
API_SECRET = "U7qxLZDxD7BXiavmzyMZIixiXQlFQ8PsYIPhxmBXXe4D5RNvOfXxS7ue42DwxLIx"
SYMBOL = "BTCUSDT"
INTERVAL = "1m"

# Connect to Binance Testnet
client = Client(API_KEY, API_SECRET, testnet=True)

# Get historical candles
def get_data():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=100)
    df = pd.DataFrame(klines, columns=[
        "time","o","h","l","c","v","ct","qav","nt","tbbav","tbqav","ignore"])
    df["c"] = df["c"].astype(float)
    return df

# Strategy
def strategy(df):
    df["ema"] = EMAIndicator(df["c"], 9).ema_indicator()
    df["rsi"] = RSIIndicator(df["c"], 14).rsi()
    latest = df.iloc[-1]

    if latest["c"] > latest["ema"] and latest["rsi"] < 70:
        return "BUY"
    elif latest["c"] < latest["ema"] and latest["rsi"] > 30:
        return "SELL"
    return "HOLD"

# Main loop
def run():
    while True:
        df = get_data()
        signal = strategy(df)
        price = df.iloc[-1]["c"]
        print(f"Signal: {signal} | Price: {price}")
        time.sleep(60)  # check every 1 minute

if __name__ == "__main__":
    run()
