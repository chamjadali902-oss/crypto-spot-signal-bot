import requests
import pandas as pd
from datetime import datetime
import traceback

# ================= CONFIG =================
BOT_TOKEN = "8408138871:AAEAFLXN-0_NX4f94DRTCfXAIY7IK5GDYmY"
CHAT_ID = "8565460915"

BASE_URL = "https://api.binance.com"
TIMEFRAME = "5m"
LIMIT = 120
TOP = 100

# ================= TELEGRAM =================
def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# ================= BINANCE =================
def get_klines(symbol, interval, limit):
    try:
        r = requests.get(
            f"{BASE_URL}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10
        )
        if r.status_code != 200:
            return None

        data = r.json()
        if not data or len(data) < 50:
            return None

        df = pd.DataFrame(data, columns=[
            "t","o","h","l","c","v","_","_","_","_","_","_"
        ])
        df = df[["o","h","l","c","v"]].astype(float)
        df.columns = ["open","high","low","close","volume"]
        return df

    except:
        return None

def get_tickers():
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/24hr", timeout=10)
        return r.json()
    except:
        return []

# ================= INDICATORS =================
def EMA(s, p):
    return s.ewm(span=p, adjust=False).mean()

def RSI(s, p=14):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(p).mean()
    avg_loss = loss.rolling(p).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================= BTC FILTER =================
def btc_safe():
    df = get_klines("BTCUSDT", "15m", 100)
    if df is None:
        return False
    price = df["close"].iloc[-1]
    ema100 = EMA(df["close"], 100).iloc[-1]
    return price >= ema100 * 0.99

# ================= STRATEGIES =================
def continuation(df):
    score = 0
    reasons = []

    if EMA(df["close"], 9).iloc[-1] > EMA(df["close"], 21).iloc[-1]:
        score += 1; reasons.append("EMA9>EMA21")

    if EMA(df["close"], 21).iloc[-1] > EMA(df["close"], 50).iloc[-1]:
        score += 1; reasons.append("EMA21>EMA50")

    rsi = RSI(df["close"]).iloc[-1]
    if 45 <= rsi <= 70:
        score += 1; reasons.append("RSI healthy")

    if df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1]:
        score += 1; reasons.append("Volume spike")

    if btc_safe():
        score += 1; reasons.append("BTC trend OK")

    return score, reasons

def reversal(df):
    score = 0
    reasons = []
    rsi = RSI(df["close"])

    if rsi.iloc[-2] < 35 and rsi.iloc[-1] > rsi.iloc[-2]:
        score += 1; reasons.append("RSI bounce")

    if EMA(df["close"], 9).iloc[-1] > EMA(df["close"], 21).iloc[-1]:
        score += 1; reasons.append("EMA reversal")

    if df["close"].iloc[-1] > df["close"].iloc[-2]:
        score += 1; reasons.append("Green candle")

    if df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1]:
        score += 1; reasons.append("Volume spike")

    return score, reasons

# ================= MAIN =================
def main():
    tg("🚀 Crypto Spot Dual Engine STARTED")

    tickers = get_tickers()
    usdt = [c for c in tickers if c.get("symbol","").endswith("USDT")]

    # CONTINUATION (Top Volume)
    for c in sorted(usdt, key=lambda x: float(x.get("quoteVolume",0)), reverse=True)[:TOP]:
        df = get_klines(c["symbol"], TIMEFRAME, LIMIT)
        if df is None:
            continue

        score, reasons = continuation(df)
        if score >= 3:
            tg(
                f"📈 CONTINUATION\n"
                f"{c['symbol']}\n"
                f"Score: {score}/5\n"
                f"{' | '.join(reasons)}"
            )

    # REVERSAL (Top Losers)
    for c in sorted(usdt, key=lambda x: float(x.get("priceChangePercent",0)))[:TOP]:
        df = get_klines(c["symbol"], TIMEFRAME, LIMIT)
        if df is None:
            continue

        score, reasons = reversal(df)
        if score >= 3:
            tg(
                f"🔄 REVERSAL\n"
                f"{c['symbol']}\n"
                f"24h: {c['priceChangePercent']}%\n"
                f"{' | '.join(reasons)}"
            )

# ================= SAFE RUN =================
if __name__ == "__main__":
    try:
        main()
        print("Bot run completed successfully")
    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()
