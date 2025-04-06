import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import os
import schedule
import time
import matplotlib.pyplot as plt 
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

def send_photo(chat_id, image_path, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        files = {'photo': photo}
        data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
        requests.post(url, files=files, data=data)

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

def fetch_ticker(symbol):
    if "." not in symbol:
        try:
            ticker = yf.Ticker(symbol + ".IS")
            _ = ticker.fast_info["lastPrice"]
            return ticker, symbol + ".IS"
        except Exception:
            pass
    ticker = yf.Ticker(symbol)
    return ticker, symbol

def process_user_requests(last_update_id):
    """
    Telegram'dan gelen güncellemeleri kontrol eder.
    Kullanıcının gönderdiği metin, direkt hisse sembolü olarak kabul edilir.
    Eğer sembol nokta içermiyorsa, otomatik olarak '.IS' eklenir.
    Metin özetinin yanı sıra, son 1 yıl verileri üzerinden 5, 20, 50, 200 günlük hareketli ortalamaları içeren grafik gönderilir.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {}
    if last_update_id:
        params['offset'] = last_update_id
    response = requests.get(url, params=params).json()
    updates = response.get("result", [])
    for update in updates:
        last_update_id = update["update_id"] + 1  # offset güncellendi
        try:
            message = update["message"]
            chat_id = message["chat"]["id"]
            symbol = message.get("text", "").strip()  # Kullanıcının girdiği sembol
            if not symbol:
                continue

            #  Sembol işleme (otomatik '.IS' ekleme) 
            t, used_symbol = fetch_ticker(symbol)
            try:
                price = t.fast_info["lastPrice"]
                hist_short = t.history(period="2d", interval="1d")["Close"].dropna()
                if len(hist_short) >= 2:
                    prev_close = hist_short.iloc[-2]
                    change = ((price - prev_close) / prev_close) * 100
                    emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
                    reply = f"{used_symbol}: {price:,.2f} ({emoji} {change:+.2f}%)"
                else:
                    reply = f"{used_symbol}: {price:,.2f} (⚪️ Değişim yok)"
            except Exception as e:
                reply = f"{used_symbol}: Veri alınamadı. Lütfen geçerli bir hisse sembolü giriniz."
            send_message(chat_id, reply)

            # Son 1 yıl verilerini çekiyoruz.
            df = t.history(period="1y")
            if df.empty:
                continue  # Veri yoksa grafik oluşturmayız

            # Hareketli ortalamaları hesaplıyoruz
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['MA200'] = df['Close'].rolling(window=200).mean()
            
            # Grafik oluşturma
            plt.figure(figsize=(10, 6))
            plt.plot(df.index, df['Close'], label='Close', linewidth=2)
            if not df['MA5'].isnull().all():
                plt.plot(df.index, df['MA5'], label='MA5')
            if not df['MA20'].isnull().all():
                plt.plot(df.index, df['MA20'], label='MA20')
            if not df['MA50'].isnull().all():
                plt.plot(df.index, df['MA50'], label='MA50')
            if not df['MA200'].isnull().all():
                plt.plot(df.index, df['MA200'], label='MA200')
            plt.title(f"{used_symbol} - Son 1 Yıl Fiyat Grafiği")
            plt.xlabel("Tarih")
            plt.ylabel("Fiyat")
            plt.legend()
            plt.tight_layout()
            
            # Geçici dosya olarak kaydediyoruz
            image_path = f"chart_{used_symbol.replace('.', '')}.png"
            plt.savefig(image_path)
            plt.close()

            # Grafiği Telegram'a gönderme
            caption = f"{used_symbol} için son 1 yıl fiyat grafiği ve hareketli ortalamalar."
            send_photo(chat_id, image_path, caption=caption)
            if os.path.exists(image_path):
                os.remove(image_path)

        except Exception as e:
            continue
    return last_update_id

last_update_id = None

if __name__ == "__main__":
    print("🟢 Bot çalışıyor - Günlük piyasa özetleri (12:00 ve 18:00) ve hisse sorguları aktif")
    init_updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json().get("result", [])
    if init_updates:
        last_update_id = init_updates[-1]["update_id"] + 1
    else:
        last_update_id = 0

    schedule.every().day.at("09:00").do(send_market_summary_to_all)
    schedule.every().day.at("15:00").do(send_market_summary_to_all)

    while True:
        schedule.run_pending()
        last_update_id = process_user_requests(last_update_id)
        time.sleep(1)
