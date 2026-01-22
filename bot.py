import requests
import pandas as pd
from datetime import datetime

# ============ CONFIG ============
BOT_TOKEN = "8408138871:AAEAFLXN-0_NX4f94DRTCfXAIY7IK5GDYmY"
CHAT_ID = "8565460915"

BASE_URL = "https://api.binance.com"
TIMEFRAME = "5m"
LIMIT = 120
TOP = 100

# ============ TELEGRAM ============
def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# ============ BINANCE ============
def klines(symbol, interval, limit):
    try:
        r = requests.get(
            f"{BASE_URL}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10
        )
        if r.status_code != 200:
            return None

        df = pd.DataFrame(r.json(), columns=[
            "t","o","h","l","c","v","_","_","_","_","_","_"
        ])
        df = df[["o","h","l","c","v"]].astype(float)
        df.columns = ["open","high","low","close","volume"]
        return df
    except:
        return None

def tickers():
    try:
        return requests.get(f"{BASE_URL}/api/v3/ticker/24hr", timeout=10).json()
    except:
        return []

# ============ INDICATORS ============
def EMA(s, p):
    return s.ewm(span=p, adjust=False).mean()

def RSI(s, p=14):
    d = s.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = g.rolling(p).mean()
    al = l.rolling(p).mean()
    rs = ag / al
    return 100 - (100 / (1 + rs))

# ============ BTC FILTER ============
def btc_safe():
    df = klines("BTCUSDT", "15m", 100)
    if df is None:
        return False
    ema = EMA(df["close"], 100).iloc[-1]
    price = df["close"].iloc[-1]
    return price >= ema * 0.99

# ============ STRATEGIES ============
def trend(df):
    s, r = 0, []
    if EMA(df["close"],9).iloc[-1] > EMA(df["close"],21).iloc[-1]:
        s+=1; r.append("EMA9>EMA21")
    if EMA(df["close"],21).iloc[-1] > EMA(df["close"],50).iloc[-1]:
        s+=1; r.append("EMA21>EMA50")
    if 45 <= RSI(df["close"]).iloc[-1] <= 70:
        s+=1; r.append("RSI healthy")
    if df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1]:
        s+=1; r.append("Volume spike")
    if btc_safe():
        s+=1; r.append("BTC safe")
    return s, r

def reversal(df):
    s, r = 0, []
    rsi = RSI(df["close"])
    if rsi.iloc[-2] < 35 and rsi.iloc[-1] > rsi.iloc[-2]:
        s+=1; r.append("RSI bounce")
    if EMA(df["close"],9).iloc[-1] > EMA(df["close"],21).iloc[-1]:
        s+=1; r.append("EMA cross")
    if df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1]:
        s+=1; r.append("Volume spike")
    if df["close"].iloc[-1] > df["close"].iloc[-2]:
        s+=1; r.append("Green candle")
    return s, r

# ============ MAIN ============
def run():
    tg("🔁 Fresh Dual Strategy Scan Started")

    data = tickers()
    usdt = [c for c in data if c.get("symbol","").endswith("USDT")]

    # TOP VOLUME → CONTINUATION
    for c in sorted(usdt, key=lambda x: float(x.get("quoteVolume",0)), reverse=True)[:TOP]:
        df = klines(c["symbol"], TIMEFRAME, LIMIT)
        if df is None: continue
        s,r = trend(df)
        if s>=3:
            tg(f"📈 CONTINUATION\n{c['symbol']}\nScore {s}/5\n" + " | ".join(r))

    # TOP LOSERS → REVERSAL
    for c in sorted(usdt, key=lambda x: float(x.get("priceChangePercent",0)))[:TOP]:
        df = klines(c["symbol"], TIMEFRAME, LIMIT)
        if df is None: continue
        s,r = reversal(df)
        if s>=3:
            tg(f"🔄 REVERSAL\n{c['symbol']}\n24h {c['priceChangePercent']}%\n" + " | ".join(r))

if __name__ == "__main__":
    tg("🚀 Fresh Crypto Spot Engine STARTED")
    run()
