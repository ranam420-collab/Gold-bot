import os
import time
import requests
import yfinance as yf
import pandas as pd
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- PORT FIX - NO FLASK NEEDED ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot is Live!")
    def log_message(self, *args):
        pass

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# --- TELEGRAM ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("Telegram sent")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- GOLD LOGIC ---
def check_gold():
    try:
        df = yf.download("GC=F", period="5d", interval="15m", progress=False)
        if df.empty:
            print("No data from Yahoo")
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(last['Close'])
        print(f"Price: {price} EMA50: {float(last['EMA50']):.2f} EMA200: {float(last['EMA200']):.2f}")
        if float(last['EMA50']) > float(last['EMA200']) and float(prev['EMA50']) <= float(prev['EMA200']):
            send_telegram(f"🟢 GOLD BUY SIGNAL\nPrice: {price}\nEMA50 > EMA200 Cross\nSL: {price-15:.2f} TP: {price+30:.2f}")
        elif float(last['EMA50']) < float(last['EMA200']) and float(prev['EMA50']) >= float(prev['EMA200']):
            send_telegram(f"🔴 GOLD SELL SIGNAL\nPrice: {price}\nEMA50 < EMA200 Cross\nSL: {price+15:.2f} TP: {price-30:.2f}")
    except Exception as e:
        print(f"Gold Check Error: {e}")

if __name__ == "__main__":
    Thread(target=keep_alive, daemon=True).start()
    print("Keep-alive server started")
    send_telegram("🤖 Gold Bot Restarted - New Rules Active ✅")
    while True:
        check_gold()
        time.sleep(300)
