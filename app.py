import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import os
import schedule
import time
from veritabani import TOKEN

TOKEN = TOKEN
DATA_FILE = "users.json"

assets = {
    '📈 BIST100': 'XU100.IS',
    '📊 BIST30': 'XU030.IS',
    '💵 Dolar': 'USDTRY=X',
    '💶 Euro': 'EURTRY=X',
    '🥇 Altın-(USD)': 'GC=F',
    '🥈 Gümüş-(USD)': 'SI=F',
    '🟡 Bitcoin-(USD)': 'BTC-USD',
    '💎 ETH-(USD)': 'ETH-USD',
}

def get_and_save_chat_ids():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()

    ids = set()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            ids.update(json.load(f))

    for result in response.get("result", []):
        try:
            chat_id = result["message"]["chat"]["id"]
            ids.add(chat_id)
        except:
            continue

    with open(DATA_FILE, "w") as f:
        json.dump(list(ids), f)

def send_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def send_market_summary_to_all():
    print(f"📤 Gönderim başladı - {datetime.now().strftime('%H:%M:%S')}")
    get_and_save_chat_ids()

    msg = f"*📊 Günlük Piyasa Özeti - {datetime.now():%d.%m.%Y}*\n\n"
    df_all = pd.DataFrame()

    for name, symbol in assets.items():
        try:
            t = yf.Ticker(symbol)
            price = t.fast_info["lastPrice"]

            hist = t.history(period="2d", interval="1d")["Close"].dropna()
            hist.index = pd.to_datetime(hist.index.date)
            hist = hist[~hist.index.duplicated(keep="last")]
            hist.name = symbol

            df_all = df_all.join(hist, how="outer")

            if len(hist) >= 2:
                prev_close = hist.iloc[-2]
                change = ((price - prev_close) / prev_close) * 100
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
                msg += f"{name}: {price:,.2f} ({emoji} {change:+.2f}%)\n"
            else:
                msg += f"{name}: {price:,.2f} (⚪️ Değişim yok)\n"
        except Exception as e:
            msg += f"{name}: Veri alınamadı\n"

    with open(DATA_FILE, "r") as f:
        chat_ids = json.load(f)
    for chat_id in chat_ids:
        send_message(chat_id, msg)
        print(f"✅ Mesaj gönderildi: {chat_id}")


schedule.every(5).minutes.do(send_market_summary_to_all)

if __name__ == "__main__":
    print("🟢 Bot çalışıyor - Her 5 dakikada bir mesaj gönderilecek")
    while True:
        schedule.run_pending()
        time.sleep(1)
