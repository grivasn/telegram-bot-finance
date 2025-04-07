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
            hist = t.history(period="5d", interval="1d")["Close"].dropna()
            hist.index = pd.to_datetime(hist.index.date)
            hist = hist[~hist.index.duplicated(keep="last")]
            hist.name = symbol

            df_all = df_all.join(hist, how="outer")

            if len(hist) >= 2:
                current_price = hist.iloc[-1]
                prev_close = hist.iloc[-2]
                change = ((current_price - prev_close) / prev_close) * 100
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
                msg += f"{name}: {current_price:,.2f} ({emoji} {change:+.2f}%)\n"
            else:
                current_price = hist.iloc[-1]
                msg += f"{name}: {current_price:,.2f} (⚪️ Değişim yok)\n"
                
        except Exception as e:
            msg += f"{name}: Veri alınamadı\n"
            print(f"Error for {symbol}: {str(e)}")

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
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'offset': last_update_id} if last_update_id else {}
    updates = requests.get(url, params=params).json().get("result", [])
    if not updates:
        return last_update_id

    for update in updates:
        last_update_id = update["update_id"] + 1
        try:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "").strip()
            if not text:
                continue

            if text.lower() == "/start":
                get_and_save_chat_ids()
                send_message(chat_id, "*📈 Hoş Geldiniz!*\n\n"
                    "Bu bot ile hisse senedi ve piyasa verilerini takip edebilirsiniz.\n"
                    "- Günlük piyasa özetleri için saat 09:00 ve 18:00'te bildirim alırsınız.\n"
                    "- Bir hisse sembolü (örn: BIMAS) yazarak anlık fiyat ve grafik alabilirsiniz.\n")
                print(f"✅ Yeni kullanıcı: {chat_id}")
                continue

            t, symbol = fetch_ticker(text)
            price = t.fast_info.get("lastPrice", "Veri yok")
            hist = t.history(period="2d", interval="1d")["Close"].dropna()
            reply = f"{symbol}: {price:,.2f}" + (f" ({'🟢' if price > hist.iloc[-2] else '🔴' if price < hist.iloc[-2] else '⚪️'} {((price-hist.iloc[-2])/hist.iloc[-2]*100):+.2f}%)" if len(hist) >= 2 else " (⚪️)")
            send_message(chat_id, reply if price != "Veri yok" else f"{symbol}: Veri alınamadı")

            df = t.history(period="1y")
            if df.empty:
                continue
                
            for window, label in [(5,'MA5'), (20,'MA20'), (50,'MA50'), (200,'MA200')]:
                df[label] = df['Close'].rolling(window).mean()
                
            plt.figure(figsize=(10,6))
            plt.plot(df['Close'], label='Close')
            for ma in ['MA5', 'MA20', 'MA50', 'MA200']:
                if not df[ma].isnull().all():
                    plt.plot(df[ma], label=ma)
            plt.title(f"{symbol} - 1 Yıl")
            plt.legend()
            image_path = f"chart_{symbol.replace('.','')}.png"
            plt.savefig(image_path)
            plt.close()
            
            send_photo(chat_id, image_path, f"{symbol} 1 yıl grafiği")
            if os.path.exists(image_path):
                os.remove(image_path)

        except Exception as e:
            print(f"Hata (chat_id: {chat_id}): {e}")
            continue
            
    return last_update_id

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
