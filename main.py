from flask import Flask
import requests, time, threading

app = Flask(__name__)
TOKEN = "9256292431:AAHKTzk6CVCVclGWo0gam3Rb23KjCtkQqXA"
CHAT_ID = "7670492822"

prices = []
last_signal_time = 0

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def ema(arr, n):
    k = 2/(n+1)
    e = arr[0]
    for v in arr[1:]:
        e = v*k + e*(1-k)
    return e

def bot_loop():
    global last_signal_time
    while True:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
            p = float(r['price'])
            prices.append(p)
            if len(prices) > 50:
                prices.pop(0)
            if len(prices) > 21:
                e9 = ema(prices, 9)
                e21 = ema(prices, 21)
                gains = sum(max(prices[i]-prices[i-1],0) for i in range(max(1,len(prices)-14), len(prices)))
                losses = sum(max(prices[i-1]-prices[i],0) for i in range(max(1,len(prices)-14), len(prices)))
                rsi = 100 - (100/(1+(gains/losses if losses!=0 else 100)))
                is_buy = e9 > e21 and 50 < rsi < 65
                now = time.time()
                if is_buy and (now - last_signal_time) > 900:
                    last_signal_time = now
                    send(f"✅ GOLD SOLID BUY - 15 MIN TRADE\nEntry: ${p:.2f}\nSL: ${p-3:.2f}\nTP: ${p+6:.2f}\nRSI: {rsi:.1f} | EMA9 > EMA21")
            time.sleep(15)
        except:
            time.sleep(15)

threading.Thread(target=bot_loop, daemon=True).start()

@app.route('/')
def home():
    return "GOLD BOT RUNNING - FREE 24/7"

app.run(host='0.0.0.0', port=10000)
