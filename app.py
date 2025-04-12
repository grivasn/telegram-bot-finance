import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import os
import schedule
import time
import matplotlib.pyplot as plt 
from veritabani import TOKEN
import cloudscraper
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not TOKEN:
    raise ValueError("Hata: TOKEN bulunamadı. Lütfen .env dosyasında TOKEN değerini tanımlayın.")

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
    try:
        response = supabase.table("users").select("chat_id").eq("is_active", True).execute()
        return [user["chat_id"] for user in response.data]
    except Exception as e:
        print(f"Kullanıcılar yüklenirken hata: {e}")
        return []

def save_user(chat_id):
    try:
        existing = supabase.table("users").select("chat_id").eq("chat_id", chat_id).execute()
        if existing.data:
            supabase.table("users").update({"is_active": True}).eq("chat_id", chat_id).execute()
        else:
            supabase.table("users").insert({"chat_id": chat_id, "is_active": True}).execute()
        supabase.table("user_logs").insert({
            "chat_id": chat_id,
            "action": "joined"
        }).execute()
    except Exception as e:
        print(f"Kullanıcı {chat_id} kaydedilirken hata: {e}")

def deactivate_user(chat_id):
    try:
        supabase.table("users").update({"is_active": False}).eq("chat_id", chat_id).execute()
        supabase.table("user_logs").insert({
            "chat_id": chat_id,
            "action": "left"
        }).execute()
    except Exception as e:
        print(f"Kullanıcı {chat_id} pasif yapılırken hata: {e}")

def load_portfolios():
    portfolios = {}
    try:
        result = supabase.table("portfolios").select("chat_id", "symbol").execute()
        for row in result.data:
            portfolios.setdefault(str(row["chat_id"]), []).append(row["symbol"])
    except Exception as e:
        print(f"Portföyler yüklenirken hata: {e}")
    return portfolios

def save_portfolio(chat_id, symbols):
    try:
        supabase.table("portfolios").delete().eq("chat_id", chat_id).execute()
        for symbol in symbols:
            supabase.table("portfolios").insert({"chat_id": chat_id, "symbol": symbol}).execute()
    except Exception as e:
        print(f"{chat_id} için portföy kaydedilirken hata: {e}")

def get_and_save_chat_ids():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url).json()
        for result in response.get("result", []):
            try:
                chat_id = result["message"]["chat"]["id"]
                save_user(chat_id)
            except Exception:
                continue
    except Exception as e:
        print(f"Chat ID'ler alınırken hata: {e}")

def send_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if not response.ok:
            error_desc = response.json().get('description', '').lower()
            if 'bot was blocked' in error_desc or 'chat not found' in error_desc:
                deactivate_user(chat_id)
                print(f"Kullanıcı {chat_id} engelledi veya sohbet yok. Pasif yapıldı.")
        return response
    except Exception as e:
        print(f"Mesaj gönderilirken hata: {e}")
        return None

def send_photo(chat_id, image_path, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"{chat_id}'e resim gönderilirken hata: {e}")

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
                    print(f"{symbol} için hata: {str(e)}")
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
                    print(f"{symbol} için hata: {str(e)}")

        send_message(chat_id, msg)
        print(f"✅ Mesaj gönderildi: {chat_id}")

def process_user_requests(last_update_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'offset': last_update_id} if last_update_id else {}
    try:
        updates = requests.get(url, params=params).json().get("result", [])
    except Exception as e:
        print(f"Güncellemeler alınırken hata: {e}")
        return last_update_id

    if not updates:
        return last_update_id

    portfolios = load_portfolios()

    for update in updates:
        last_update_id = update["update_id"] + 1
        try:
            if "message" not in update:
                continue 

            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "").strip()
            if not text:
                continue

            if text.lower() == "/start":
                save_user(chat_id)
                send_message(chat_id, "*📈 Hoş Geldiniz!*\n\n"
                    "Bu bot ile hisse senedi ve piyasa verilerini takip edebilirsiniz.\n"
                    "- Günlük piyasa özetleri için belirlenen saatlerde bildirim alırsınız.\n"
                    "- Bir hisse sembolü (örneğin: BIMAS) yazarak anlık fiyatını, banka ve yatırım kuruluşlarının tavsiyelerini, hedef fiyatlarını ve hisse grafiğini görüntüleyebilirsiniz.\n"
                    "- /add <hisse> ile portföyünüze hisse ekleyebilir,\n"
                    "  /remove <hisse> ile portföyünüzden çıkarabilir,\n"
                    "  /portfoy ile portföyünüzü görebilir,\n"
                    "  /stop ile bildirimleri durdurabilirsiniz.")
                print(f"✅ Yeni kullanıcı: {chat_id}")
                continue

            if text.lower() == "/stop":
                deactivate_user(chat_id)
                send_message(chat_id, "*📉 Bildirimler durduruldu.*\n"
                    "Tekrar bildirim almak için /start komutunu kullanabilirsiniz.")
                print(f"❌ Kullanıcı bildirimleri durdurdu: {chat_id}")
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
                save_portfolio(chat_id, portfolios[str(chat_id)])
                continue

            if text.lower() == "/live":
                user_portfolio = portfolios.get(str(chat_id), [])
                if user_portfolio:
                    msg = "*📊 Canlı Portföyünüz:*\n\n"
                    for symbol in user_portfolio:
                        try:
                            t, symbol_full = fetch_ticker(symbol)
                            price = t.fast_info.get("lastPrice", None)
                            if price is None:
                                msg += f"{symbol}: Veri alınamadı\n"
                                continue
                            hist = t.history(period="2d", interval="1d")["Close"].dropna()
                            if len(hist) >= 2:
                                prev_close = hist.iloc[-2]
                                change = ((price - prev_close) / prev_close) * 100
                                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
                                msg += f"{symbol_full}: {price:,.2f} ({emoji} {change:+.2f}%)\n"
                            else:
                                msg += f"{symbol_full}: {price:,.2f} (⚪️)\n"
                        except Exception as e:
                            msg += f"{symbol}: Veri alınamadı\n"
                    send_message(chat_id, msg)
                else:
                    send_message(chat_id, "Portföyünüz boş. /add <hisse> komutuyla portföyünüze hisse ekleyebilirsiniz.")
                continue

            if text.lower().startswith("/remove "):
                ticker_to_remove = text[8:].strip().upper()
                if str(chat_id) in portfolios and ticker_to_remove in portfolios[str(chat_id)]:
                    portfolios[str(chat_id)].remove(ticker_to_remove)
                    send_message(chat_id, f"✅ *{ticker_to_remove}* portföyünüzden çıkarıldı.")
                    save_portfolio(chat_id, portfolios[str(chat_id)])
                else:
                    send_message(chat_id, f"🔔 *{ticker_to_remove}* portföyünüzde bulunamadı.")
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

            try:
                scraper = cloudscraper.CloudScraper()
                url = "https://api.fintables.com/analyst-ratings/?brokerage_id=&code=&in_model_portfolio"
                r = scraper.get(url).json()["results"]
                df = pd.DataFrame(r)

                df["title"] = df["brokerage"].apply(lambda x: x.get("title") if isinstance(x, dict) else None)
                columns_order = ["code", "title", "type", "published_at", "price_target", "in_model_portfolio"]
                df = df[columns_order]

                df["published_at"] = pd.to_datetime(df["published_at"]).dt.strftime("%Y-%m-%d")
                df.columns = ["Hisse Kodu", "Kurum", "Öneri", "Öneri Tarihi", "Fiyat Hedefi", "Model Portföy"]
                df["Model Portföy"] = df["Model Portföy"].replace({True: "Var", False: "Yok"})

                öneri_df = df[df["Hisse Kodu"] == text.upper()]

                if not öneri_df.empty:
                    fig, ax = plt.subplots(figsize=(12, len(öneri_df) * 0.6 + 1))
                    ax.axis('tight')
                    ax.axis('off')
                    table = ax.table(cellText=öneri_df.values, colLabels=öneri_df.columns, loc='center', cellLoc='center')
                    table.auto_set_font_size(False)
                    table.set_fontsize(10)
                    table.scale(1.1, 1.1)

                    öneri_image_path = f"oneriler_{text.upper()}.png"
                    plt.tight_layout()
                    plt.savefig(öneri_image_path, bbox_inches="tight", dpi=200)
                    plt.close()

                    send_photo(chat_id, öneri_image_path, f"🔎 *{text.upper()} için Analist Önerileri*")
                    if os.path.exists(öneri_image_path):
                        os.remove(öneri_image_path)
            except Exception as e:
                print(f"Fintables veri hatası: {e}")

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
            print(f"Hata (update_id: {update['update_id']}): {e}")
            continue

    return last_update_id

if __name__ == "__main__":
    print("🟢 Bot çalışıyor - Günlük piyasa özetleri ve hisse sorguları aktif")
    try:
        init_updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json().get("result", [])
        if init_updates:
            last_update_id = init_updates[-1]["update_id"] + 1
        else:
            last_update_id = 0
    except Exception as e:
        print(f"Güncellemeler başlatılırken hata: {e}")
        last_update_id = 0

    schedule.every().day.at("09:00").do(send_market_summary_to_all)
    schedule.every().day.at("15:00").do(send_market_summary_to_all)

    while True:
        schedule.run_pending()
        last_update_id = process_user_requests(last_update_id)
        time.sleep(1)
