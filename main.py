import os
import time
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- RENDER PORT FIX - Web Service ko port chahiye hota hai ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot is Running")
    def log_message(self, format, *args):
        return

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Keep-alive server started on port {port}")

keep_alive()

# --- SETTINGS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"  # Gold Futures

SAUDI_TZ = pytz.timezone("Asia/Riyadh")
START_HOUR = 7   # 7 AM Saudi
END_HOUR = 22    # 10 PM Saudi
MAX_SIGNALS_PER_DAY = 8
COUNT_FILE = "signals_today.json"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def is_trading_time():
    now = datetime.now(SAUDI_TZ)
    return START_HOUR <= now.hour < END_HOUR

def get_signal_count():
    today = datetime.now(SAUDI_TZ).strftime("%Y-%m-%d")
    try:
        with open(COUNT_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") == today:
                return data.get("count", 0)
    except:
        pass
    return 0

def save_signal_count(count):
    today = datetime.now(SAUDI_TZ).strftime("%Y-%m-%d")
    with open(COUNT_FILE, "w") as f:
        json.dump({"date": today, "count": count}, f)

def get_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_signal():
    # Time Filter
    if not is_trading_time():
        print("Outside trading time 7AM-10PM Saudi, sleeping")
        return

    # Daily Limit Filter - 4 to 8 signals
    count = get_signal_count()
    if count >= MAX_SIGNALS_PER_DAY:
        print(f"Daily limit reached: {count}/8")
        return

    # Get Gold 15M Data
    df = yf.download(SYMBOL, interval="15m", period="2d", progress=False)
    if df.empty or len(df) < 210:
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df['Close']
    df['EMA50'] = close.ewm(span=50).mean()
    df['EMA200'] = close.ewm(span=200).mean()
    df['RSI'] = get_rsi(close)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(last['Close'])
    ema50 = float(last['EMA50'])
    ema200 = float(last['EMA200'])
    rsi = float(last['RSI'])
    prev_close = float(prev['Close'])

    print(f"Price: {price} | EMA50: {ema50:.2f} | EMA200: {ema200:.2f} | RSI: {rsi:.2f} | Count: {count}")

    signal = None

    # --- STRONG BUY - 3 Conditions Must Match ---
    # 1. Trend UP: Price > EMA50 > EMA200
    # 2. RSI Strong: 50 to 68 (not overbought)
    # 3. Candle Confirmation: Last candle GREEN and closed above prev close
    if price > ema50 > ema200 and 50 < rsi < 68 and price > prev_close:
        sl = price - 3.0
        tp = price + 6.0  # 1:2 Risk Reward
        signal = f"✅ GOLD SOLID BUY - 15 MIN TRADE\n\nPrice: ${price:.2f}\nEntry: ${price:.2f}\nSL: ${sl:.2f}\nTP: ${tp:.2f}\n\nRSI: {rsi:.1f}\nEMA50: {ema50:.2f}\nEMA200: {ema200:.2f}\n\n⏰ Saudi Time: {datetime.now(SAUDI_TZ).strftime('%I:%M %p')}\n🎯 High Confidence Signal {count+1}/8 Today"

    # --- STRONG SELL - 3 Conditions Must Match ---
    elif price < ema50 < ema200 and 32 < rsi < 50 and price < prev_close:
        sl = price + 3.0
        tp = price - 6.0
        signal = f"🔻 GOLD SOLID SELL - 15 MIN TRADE\n\nPrice: ${price:.2f}\nEntry: ${price:.2f}\nSL: ${sl:.2f}\nTP: ${tp:.2f}\n\nRSI: {rsi:.1f}\nEMA50: {ema50:.2f}\nEMA200: {ema200:.2f}\n\n⏰ Saudi Time: {datetime.now(SAUDI_TZ).strftime('%I:%M %p')}\n🎯 High Confidence Signal {count+1}/8 Today"

    if signal:
        send_telegram(signal)
        save_signal_count(count + 1)
        print("STRONG Signal Sent!")
    else:
        print("No Strong Signal - Skipped weak signal")

# --- MAIN LOOP ---
if __name__ == "__main__":
    send_telegram("🤖 Gold Bot Restarted - New Rules Active ✅\n\n⏰ Time: 7 AM - 10 PM Saudi\n🎯 Only STRONG Signals\n📊 Max 8 Signals / Day")
    while True:
        try:
            check_signal()
        except Exception as e:
            print(f"Error: {e}")
        # Check every 5 min
        time.sleep(300)
