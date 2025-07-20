import ccxt
import pandas as pd
import time
import requests
from datetime import datetime, timedelta

# === НАСТРОЙКИ ===
API_KEY = 'Q6CWqvufTGiYgyHVTESDdtzpCAWb8CllWlw6sr6FLitQg1PCAB3d6GN5HXx8HtgR'
API_SECRET = '8XaR3fjStTWrGJRm6vNtFXkJSf7O9CN0khykWcQ6HGsEaUcjY4r7tAxOzf09tAC4'  # Только для чтения

TELEGRAM_TOKEN = '8042877270:AAH8Iww9NPD5tEg4_SDbENxPpVoQVTEbKok'
CHAT_IDS = ['398490289', '339561664']  # Добавь другие chat_id через запятую, например: '123456789'

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
TIMEFRAMES = ['15m', '1h']
LOOKBACK_BARS = 20
RR_RATIO = 2

# === BINANCE API ===
binance = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in CHAT_IDS:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"[Ошибка Telegram для {chat_id}] {e}")



def fetch_ohlcv(symbol, timeframe, limit):
    data = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def detect_fakeout(df):
    recent_lows = df['low'][-LOOKBACK_BARS:-1]
    recent_highs = df['high'][-LOOKBACK_BARS:-1]
    key_low = recent_lows.min()
    key_high = recent_highs.max()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if prev['low'] < key_low and last['close'] > prev['close'] and last['volume'] > df['volume'].mean():
        entry = last['close']
        stop = prev['low']
        take = entry + (entry - stop) * RR_RATIO
        return 'LONG', key_low, entry, stop, take
    elif prev['high'] > key_high and last['close'] < prev['close'] and last['volume'] > df['volume'].mean():
        entry = last['close']
        stop = prev['high']
        take = entry - (stop - entry) * RR_RATIO
        return 'SHORT', key_high, entry, stop, take

    return None, None, None, None, None


def run_bot():
    print("[INFO] Старт анализа рынка...")
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            df = fetch_ohlcv(symbol, timeframe, LOOKBACK_BARS + 2)
            signal, level, entry, stop, take = detect_fakeout(df)

            if signal:
                message = (f"\n🚨 <b>СИГНАЛ</b> ({symbol}, TF: {timeframe}): <b>{signal}</b>\n"
                           f"🔹 Уровень ликвидности: <b>{level:.2f}</b>\n"
                           f"📈 Вход: <b>{entry:.2f}</b>\n🛑 Стоп: <b>{stop:.2f}</b>\n🎯 Тейк: <b>{take:.2f}</b>")
                print(message)
                send_telegram_message(message)
            else:
                print(f"[{symbol} | {timeframe}] — сигнала нет.")


def loop():
    while True:
        run_bot()
        print("Ждём 1 минуту...")
        time.sleep(60)


if __name__ == '__main__':
    loop()

