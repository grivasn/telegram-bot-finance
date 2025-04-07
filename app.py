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
USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolios.json"


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

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_users(user_ids):
    with open(USERS_FILE, "w") as f:
        json.dump(list(user_ids), f)

def load_portfolios():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}

def save_portfolios(portfolios):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolios, f)

def get_and_save_chat_ids():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()
    ids = set(load_users())

    for result in response.get("result", []):
        try:
            chat_id = result["message"]["chat"]["id"]
            ids.add(chat_id)
        except Exception:
            continue

    save_users(ids)

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

def send_market_summary_to_all():
    print(f"📤 Gönderim başladı - {datetime.now().strftime('%H:%M:%S')}")
    get_and_save_chat_ids()
    users = load_users()
    portfolios = load_portfolios()

    for chat_id in users:
        chat_portfolio = portfolios.get(str(chat_id), [])
        msg = f"*📊 Günlük Piyasa Özeti - {datetime.now():%d.%m.%Y}*\n\n"
        df_all = pd.DataFrame()

        if chat_portfolio:
            for symbol in chat_portfolio:
                try:
                    t, symbol_full = fetch_ticker(symbol)
                    hist = t.history(period="5d", interval="1d")["Close"].dropna()
                    hist.index = pd.to_datetime(hist.index.date)
                    hist = hist[~hist.index.duplicated(keep="last")]
                    hist.name = symbol_full

                    df_all = df_all.join(hist, how="outer")

                    if len(hist) >= 2:
                        current_price = hist.iloc[-1]
                        prev_close = hist.iloc[-2]
                        change = ((current_price - prev_close) / prev_close) * 100
                        emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
                        msg += f"{symbol_full}: {current_price:,.2f} ({emoji} {change:+.2f}%)\n"
                    else:
                        current_price = hist.iloc[-1]
                        msg += f"{symbol_full}: {current_price:,.2f} (⚪️ Değişim yok)\n"
                except Exception as e:
                    msg += f"{symbol}: Veri alınamadı\n"
                    print(f"Error for {symbol}: {str(e)}")
        else:

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

        send_message(chat_id, msg)
        print(f"✅ Mesaj gönderildi: {chat_id}")

def process_user_requests(last_update_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'offset': last_update_id} if last_update_id else {}
    updates = requests.get(url, params=params).json().get("result", [])
    if not updates:
        return last_update_id

    portfolios = load_portfolios()

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
                    "- Günlük piyasa özetleri için belirlenen saatlerde bildirim alırsınız.\n"
                    "- Bir hisse sembolü (örn: BIMAS) yazarak anlık fiyat ve grafik alabilirsiniz.\n"
                    "- /add <hisse> ile portföyünüze hisse ekleyebilir,\n"
                    "  /remove <hisse> ile portföyünüzden çıkarabilir,\n"
                    "  /portfoy ile portföyünüzü görebilirsiniz.")
                print(f"✅ Yeni kullanıcı: {chat_id}")
                continue

            if text.lower().startswith("/add "):
                ticker_to_add = text[5:].strip().upper()

                try:
                    t, _ = fetch_ticker(ticker_to_add)
                    price = t.fast_info.get("lastPrice", None)
                    if price is None:
                        send_message(chat_id, f"🔔 *{ticker_to_add}* bulunamadı.")
                        continue  
                except Exception:
                    send_message(chat_id, f"🔔 *{ticker_to_add}* bulunamadı.")
                    continue

                portfolios.setdefault(str(chat_id), [])
                if ticker_to_add in portfolios[str(chat_id)]:
                    send_message(chat_id, f"🔔 *{ticker_to_add}* zaten portföyünüzde mevcut.")
                else:
                    portfolios[str(chat_id)].append(ticker_to_add)
                    send_message(chat_id, f"✅ *{ticker_to_add}* portföyünüze eklendi.")
                save_portfolios(portfolios)
                continue

            if text.lower().startswith("/remove "):
                ticker_to_remove = text[8:].strip().upper()
                if str(chat_id) in portfolios and ticker_to_remove in portfolios[str(chat_id)]:
                    portfolios[str(chat_id)].remove(ticker_to_remove)
                    send_message(chat_id, f"✅ *{ticker_to_remove}* portföyünüzden çıkarıldı.")
                else:
                    send_message(chat_id, f"🔔 *{ticker_to_remove}* portföyünüzde bulunamadı.")
                save_portfolios(portfolios)
                continue

            if text.lower() == "/portfoy":
                user_portfolio = portfolios.get(str(chat_id), [])
                if user_portfolio:
                    port_text = "*📋 Portföyünüz:*\n" + "\n".join(f"- {ticker}" for ticker in user_portfolio)
                else:
                    port_text = "Portföyünüz boş. /add <hisse> komutuyla portföyünüze hisse ekleyebilirsiniz."
                send_message(chat_id, port_text)
                continue

            t, symbol = fetch_ticker(text.upper())
            price = t.fast_info.get("lastPrice", "Veri yok")
            hist = t.history(period="2d", interval="1d")["Close"].dropna()
            if len(hist) >= 2:
                change = ((price - hist.iloc[-2]) / hist.iloc[-2]) * 100
                emoji = "🟢" if price > hist.iloc[-2] else "🔴" if price < hist.iloc[-2] else "⚪️"
                reply = f"{symbol}: {price:,.2f} ({emoji} {change:+.2f}%)"
            else:
                reply = f"{symbol}: {price:,.2f} (⚪️)"
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
            plt.title(f"{symbol} - 1 Yıllık Grafiği")
            plt.legend()
            image_path = f"chart_{symbol.replace('.','')}.png"
            plt.savefig(image_path)
            plt.close()
            send_photo(chat_id, image_path, f"{symbol} 1 Yıllık Grafiği")
            if os.path.exists(image_path):
                os.remove(image_path)

        except Exception as e:
            print(f"Hata (chat_id: {chat_id}): {e}")
            continue

    return last_update_id

if __name__ == "__main__":
    print("🟢 Bot çalışıyor - Günlük piyasa özetleri ve hisse sorguları aktif")
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
