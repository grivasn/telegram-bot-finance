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
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import glob
import tempfile
from bs4 import BeautifulSoup
import seaborn as sns

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not TOKEN:
    raise ValueError("Hata: TOKEN bulunamadı. Lütfen .env dosyasında TOKEN değerini tanımlayın.")

download_dir = os.path.abspath("downloads")
os.makedirs(download_dir, exist_ok=True)
excel_file_path = os.path.join(download_dir, "tefas_funds.xls")

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

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    temp_profile = tempfile.mkdtemp()
    opts.add_argument(f"--user-data-dir={temp_profile}")

    opts.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = Chrome(options=opts)

    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": download_dir
    })

    print("✅ Chrome başlatıldı, geçici profil:", temp_profile)
    return driver

def download_excel(max_attempts=5, initial_wait=15, retry_wait=10):
    attempt = 1
    while attempt <= max_attempts:
        print(f"📥 Excel indirme denemesi {attempt}/{max_attempts}...")
        
        with setup_driver() as driver:
            driver.get("https://www.tefas.gov.tr/FonKarsilastirma.aspx")
            try:
                btn = WebDriverWait(driver, 40).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="table_fund_returns_wrapper"]//button[3]'))
                )
                btn.click()

                print("📥 Excel indirme butonuna tıklandı, bekleniyor...")
                time.sleep(initial_wait)  

                print("📂 İndirilen klasör içeriği:", os.listdir(download_dir))
                file = next(iter(glob.glob(os.path.join(download_dir, "*.xls*"))), None)

                if not file:
                    print("❌ Dosya bulunamadı.")
                    attempt += 1
                    time.sleep(retry_wait)
                    continue

                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
                os.rename(file, excel_file_path)

                file_size = os.path.getsize(excel_file_path)
                print(f"📏 Dosya boyutu: {file_size} byte")

                if file_size < 1024:
                    print(f"❌ Dosya boş görünüyor (boyut: {file_size} byte). Tekrar deneniyor...")
                    attempt += 1
                    time.sleep(retry_wait)
                    continue


                try:
                    df = pd.read_excel(excel_file_path)
                    if df.empty:
                        print("❌ Dosya içeriği boş. Tekrar deneniyor...")
                        attempt += 1
                        time.sleep(retry_wait)
                        continue
                    else:
                        print(f"✅ Excel başarıyla indirildi: {excel_file_path}")
                        print(f"📊 Dosyada {len(df)} satır veri bulundu.")
                        return True

                except Exception as e:
                    print(f"❌ Dosya okunamadı veya bozuk: {e}. Tekrar deneniyor...")
                    attempt += 1
                    time.sleep(retry_wait)
                    continue

            except Exception as e:
                print(f"❌ Excel indirme hatası: {e}")
                attempt += 1
                time.sleep(retry_wait)
                continue

    print(f"❌ Maksimum deneme sayısına ulaşıldı ({max_attempts}). Excel dosyası indirilemedi.")
    return False

def check_excel_and_redownload():
    print(f"📋 Excel dosyası kontrol ediliyor - {datetime.now().strftime('%H:%M:%S')}")

    if not os.path.exists(excel_file_path):
        print("🔔 Excel dosyası bulunamadı, tekrar indiriliyor...")
        download_excel()
        return

    try:
        df = pd.read_excel(excel_file_path)
        row_count = len(df)

        if row_count < 10:
            print(f"🔔 Excel dosyasında {row_count} satır var (10'dan az). Tekrar indiriliyor...")
            download_excel()
        else:
            print(f"✅ Excel dosyasında {row_count} satır var, sorun yok.")

    except Exception as e:
        print(f"❌ Excel dosyası okunurken hata: {e}. Tekrar indiriliyor...")
        download_excel()

def fetch_fon_data(kullanici_fon, chat_id):
    if not os.path.exists(excel_file_path):
        print("Excel dosyası bulunamadı, indiriliyor...")
        if not download_excel():
            send_message(chat_id, "Excel dosyası indirilemedi, işlem iptal edildi.")
            return

    try:
        fon_kodlari = pd.Series(pd.read_excel(excel_file_path).iloc[:, 0]).dropna().unique()[1:]
    except Exception as e:
        send_message(chat_id, f"Excel okuma hatası: {e}")
        return

    if kullanici_fon not in fon_kodlari:
        send_message(chat_id, f"🔔 *{kullanici_fon}* fon kodu bulunamadı.")
        return

    with setup_driver() as driver:
        driver.get(f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={kullanici_fon}")
        
        xpaths = {
            "Fiyat": '//*[@id="MainContent_PanelInfo"]/div[1]/ul[1]/li[1]/span',
            "Günlük Getiri": '//*[@id="MainContent_PanelInfo"]/div[1]/ul[1]/li[2]/span',
            "Yatırımcı Sayısı": '//*[@id="MainContent_PanelInfo"]/div[1]/ul[2]/li[2]/span',
            "Fon Risk Seviyesi": '//*[@id="MainContent_DetailsViewFund"]/tbody/tr[15]/td[2]',
            "Son 1 Ay Getirisi": '//*[@id="MainContent_PanelInfo"]/div[2]/ul/li[1]/span',
            "Son 3 Ay Getirisi": '//*[@id="MainContent_PanelInfo"]/div[2]/ul/li[2]/span',
            "Son 6 Ay Getirisi": '//*[@id="MainContent_PanelInfo"]/div[2]/ul/li[3]/span',
            "Son 1 Yıl Getirisi": '//*[@id="MainContent_PanelInfo"]/div[2]/ul/li[4]/span'
        }
        
        data = {"Fon Adı": kullanici_fon}
        for key, xpath in xpaths.items():
            try:
                data[key] = WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                ).text
            except Exception:
                data[key] = "Bilgi alınamadı"

        df = pd.DataFrame([data])
        msg = f"*📈 Fon Bilgileri: {kullanici_fon}*\n\n"
        for key, value in data.items():
            if key != "Fon Adı":
                msg += f"{key}: {value}\n"
        send_message(chat_id, msg)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'tr-TR,tr;q=0.9',
        'Referer': 'https://www.tefas.gov.tr/',
    }
    cookies = {
        'ASP.NET_SessionId': 'xyz123',
    }

    try:
        with requests.get(f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={kullanici_fon}", headers=headers, cookies=cookies, timeout=10) as url:
            data = url.content
        soup = BeautifulSoup(data, features="html.parser")
        js_text = soup.find_all('script', type="text/javascript")
        
        kacinci = None
        for fiyat in range(len(js_text)):
            if len(js_text[fiyat].contents) == 0:
                continue
            if js_text[fiyat].contents[0].find("chartMainContent_FonFiyatGrafik") > 0:
                kacinci = fiyat
                break
        
        if kacinci is None:
            send_message(chat_id, f"🔔 *{kullanici_fon}* için fiyat grafiği verisi bulunamadı.")
            return

        tarih_rakam = js_text[kacinci].contents[0].split("categories")
        tarih = tarih_rakam[1].split("]")[0].split("[")[1]
        rakam = tarih_rakam[1].split("[")[4].split("]")[0]

        df = pd.DataFrame(columns=["Tarih", "Fiyat"])
        df["Tarih"] = tarih.split(",")
        df["Fiyat"] = rakam.split(",")

        df["Tarih"] = df["Tarih"].str.replace('"', '')
        df["Fiyat"] = df["Fiyat"].str.replace('"', '')

        df["Tarih"] = pd.to_datetime(df["Tarih"], format="%d.%m.%Y")
        df["Fiyat"] = pd.to_numeric(df["Fiyat"], errors='coerce')

        plt.figure(figsize=(10, 6))
        plt.plot(df["Tarih"], df["Fiyat"], label="Fiyat")
        plt.title(f"{kullanici_fon} - Fiyat Grafiği")
        plt.xlabel("Tarih")
        plt.ylabel("Fiyat")
        plt.legend()

        image_path = f"fon_chart_{kullanici_fon}.png"
        plt.savefig(image_path, bbox_inches="tight", dpi=200)
        plt.close()

        send_photo(chat_id, image_path, f"*{kullanici_fon}* 1 Yıllık Fiyat Grafiği")

        if os.path.exists(image_path):
            os.remove(image_path)

    except Exception as e:
        send_message(chat_id, f"🔔 *{kullanici_fon}* için fiyat grafiği oluşturulurken hata: {e}")
        print(f"Fiyat grafiği hatası: {e}")

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
        result = supabase.table("portfolios").select("chat_id", "symbol", "quantity", "avg_price").execute()
        for row in result.data:
            chat_id = str(row["chat_id"])
            if chat_id not in portfolios:
                portfolios[chat_id] = []
            portfolios[chat_id].append({
                "symbol": row["symbol"],
                "quantity": row["quantity"],
                "avg_price": row["avg_price"]
            })
    except Exception as e:
        print(f"Portföyler yüklenirken hata: {e}")
    return portfolios

def save_portfolio(chat_id, portfolio):
    try:
        supabase.table("portfolios").delete().eq("chat_id", chat_id).execute()
        for item in portfolio:
            supabase.table("portfolios").insert({
                "chat_id": chat_id,
                "symbol": item["symbol"],
                "quantity": item["quantity"],
                "avg_price": item["avg_price"]
            }).execute()
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

def save_alert(chat_id, symbol, target_price):
    try:
        supabase.table("alerts").insert({
            "chat_id": chat_id,
            "symbol": symbol.upper(),
            "target_price": float(target_price)
        }).execute()
    except Exception as e:
        print(f"Alarm kaydedilirken hata: {e}")

def remove_alert(chat_id, symbol):
    try:
        supabase.table("alerts").delete().eq("chat_id", chat_id).eq("symbol", symbol.upper()).execute()
    except Exception as e:
        print(f"Alarm silinirken hata: {e}")

def get_alerts(chat_id):
    try:
        response = supabase.table("alerts").select("symbol", "target_price").eq("chat_id", chat_id).execute()
        return response.data
    except Exception as e:
        print(f"Alarmlar alınırken hata: {e}")
        return []

def check_alerts():
    print(f"🔍 Alarm kontrolü başladı - {datetime.now().strftime('%H:%M:%S')}")
    users = load_users()
    for chat_id in users:
        alerts = get_alerts(chat_id)
        if not alerts:
            continue
        for alert in alerts:
            symbol = alert["symbol"]
            target_price = alert["target_price"]
            try:
                t, symbol_full = fetch_ticker(symbol)
                current_price = t.fast_info.get("lastPrice", None)
                if current_price is None:
                    continue
                if abs(current_price - target_price) <= 0.01:
                    send_message(
                        chat_id,
                        f"🔔 *{symbol_full}* hedef fiyata ulaştı!\n"
                        f"Hedef: {target_price:,.2f}\n"
                        f"Şu anki fiyat: {current_price:,.2f}"
                    )
                    remove_alert(chat_id, symbol)
                    print(f"✅ {chat_id} için {symbol} alarmı tetiklendi ve silindi.")
            except Exception as e:
                print(f"{symbol} alarm kontrolünde hata: {e}")

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

def send_live_visualization(chat_id, user_portfolio):

    df = pd.DataFrame(user_portfolio)
    df['current_price'] = df['symbol'].apply(
        lambda sym: fetch_ticker(sym)[0].fast_info.get("lastPrice", 0)
    )
    df['cost']  = df['quantity'] * df['avg_price']
    df['value'] = df['quantity'] * df['current_price']
    df['pnl']   = df['value'] - df['cost']

    total_cost  = df['cost'].sum()
    total_value = df['value'].sum()
    total_pnl   = df['pnl'].sum()
    total_roi   = (total_pnl / total_cost * 100) if total_cost else 0

    sns.set_style('whitegrid')
    colors = sns.color_palette('tab20', n_colors=len(df))

    height = max(6, len(df) * 0.4)
    fig, ax = plt.subplots(figsize=(8, height))

    wedges, texts, autotexts = ax.pie(
        df['value'],
        labels=None,
        startangle=90,
        colors=colors,
        wedgeprops={'edgecolor':'white', 'linewidth':1},
        pctdistance=0.75,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 1 else ""
    )

    labels = [
        f"{sym} ({int(q)} adet)\nK/Z: {pnl:,.2f} ({(pnl/cost*100):+.2f}%)"
        for sym, q, pnl, cost in zip(
            df['symbol'], df['quantity'], df['pnl'], df['cost']
        )
    ]
    ax.legend(
        wedges,
        labels,
        title="Portföyünüz",
        bbox_to_anchor=(1, 0.5),
        loc="center left",
        fontsize=10
    )

    centre_circle = plt.Circle((0, 0), 0.60, fc='white')
    ax.add_artist(centre_circle)
    ax.axis('equal')
    ax.set_title('Portföy Dağılımı', pad=20)

    plt.subplots_adjust(left=0.0, right=0.75, bottom=0.25)

    table_data = [[
        f"{total_cost:,.2f}",
        f"{total_value:,.2f}",
        f"{total_pnl:,.2f} ({total_roi:+.2f}%)"
    ]]
    col_labels = ["Maliyet", "Değer", "Kâr/Zarar"]
    table = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc='center',
        loc='bottom',
        bbox=[0.0, -0.22, 0.75, 0.15] 
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    plt.tight_layout()

    image_path = os.path.join(download_dir, f"live_portfolio_{chat_id}.png")
    plt.savefig(image_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    send_photo(chat_id, image_path, caption="*📊 Canlı Portföy Görseliniz*")
    os.remove(image_path)


def send_market_summary_to_all():
    print(f"📤 Gönderim başladı - {datetime.now().strftime('%H:%M:%S')}")
    get_and_save_chat_ids()
    users = load_users()
    portfolios = load_portfolios()

    for chat_id in users:
        chat_portfolio = portfolios.get(str(chat_id), [])
        msg = f"*📊 Günlük Piyasa Özeti - {datetime.now():%d.%m.%Y}*\n\n"

        if chat_portfolio:
            msg += "*Portföyünüz:*\n"
            for item in chat_portfolio:
                symbol = item["symbol"]
                try:
                    t, symbol_full = fetch_ticker(symbol)
                    hist = t.history(period="5d", interval="1d")["Close"].dropna()
                    hist.index = pd.to_datetime(hist.index.date)
                    hist = hist[~hist.index.duplicated(keep="last")]

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
            msg += "*Piyasa Özeti:*\n"
            for name, symbol in assets.items():
                try:
                    t = yf.Ticker(symbol)
                    hist = t.history(period="5d", interval="1d")["Close"].dropna()
                    hist.index = pd.to_datetime(hist.index.date)
                    hist = hist[~hist.index.duplicated(keep="last")]

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

    fon_kodlari = []
    if os.path.exists(excel_file_path):
        try:
            fon_kodlari = pd.Series(pd.read_excel(excel_file_path).iloc[:, 0]).dropna().unique()[1:]
        except Exception as e:
            print(f"Excel okuma hatası (fon kodları): {e}")

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
                    "Bu bot ile hisse senedi, fon ve piyasa verilerini takip edebilirsiniz.\n"
                    "- Günlük piyasa özetleri için 09:00 ve 15:00 saatlerinde bildirim alırsınız.\n"
                    "- Bir hisse sembolü (örneğin: BIMAS) veya fon kodu (örneğin: TLY) yazarak anlık fiyatını, analizlerini ve grafiğini görüntüleyebilirsiniz.\n"
                    "- /add <hisse> <adet> ile portföyünüze hisse ekleyebilir,\n"
                    "- /remove <hisse> ile котороеportföyünüzden çıkarabilir,\n"
                    "- /portfoy ile portföyünüzü görebilir,\n"
                    "- /stop ile bildirimleri durdurabilirsiniz.\n"
                    "- /live ile portföy hisse ve kripto paralarınızın canlı fiyatlarını, düne göre değişimlerini ve kâr/zararınızı görebilirsiniz.\n"
                    "- /alert <hisse> <fiyat> ile hedef fiyat alarmı oluşturabilirsiniz.\n"
                    "- /remove\\_alert <hisse> ile hedef fiyat alarmını kaldırabilirsiniz.\n"
                    "- /alert\\_list ile aktif alarmlarınızı görebilirsiniz.\n\n"
                )
                print(f"✅ Yeni kullanıcı: {chat_id}")
                continue

            if text.lower() == "/stop":
                deactivate_user(chat_id)
                send_message(chat_id, "*📉 Bildirimler durduruldu.*\n"
                    "Tekrar bildirim almak için /start komutunu kullanabilirsiniz.")
                print(f"❌ Kullanıcı bildirimleri durdurdu: {chat_id}")
                continue

            if text.lower().startswith("/add "):
                try:
                    parts = text.split()
                    if len(parts) != 3:
                        send_message(chat_id, "Lütfen doğru formatta girin: /add HİSSE ADET")
                        continue
                    ticker_to_add = parts[1].strip().upper()
                    quantity = float(parts[2].strip())
                    if quantity <= 0:
                        send_message(chat_id, "Adet pozitif bir sayı olmalıdır.")
                        continue

                    t, symbol_full = fetch_ticker(ticker_to_add)
                    current_price = t.fast_info.get("lastPrice", None)
                    if current_price is None:
                        send_message(chat_id, f"🔔 *{ticker_to_add}* bulunamadı.")
                        continue

                    portfolios.setdefault(str(chat_id), [])
                    existing_stock = next((item for item in portfolios[str(chat_id)] if item["symbol"] == ticker_to_add), None)

                    if existing_stock:
                        old_quantity = existing_stock["quantity"]
                        old_avg_price = existing_stock["avg_price"]
                        new_quantity = old_quantity + quantity
                        new_avg_price = ((old_quantity * old_avg_price) + (quantity * current_price)) / new_quantity
                        existing_stock["quantity"] = new_quantity
                        existing_stock["avg_price"] = new_avg_price
                        send_message(chat_id, f"✅ *{ticker_to_add}* portföyünüze eklendi.\n"
                                             f"Yeni adet: {new_quantity}, Ortalama fiyat: {new_avg_price:,.2f}")
                    else:
                        portfolios[str(chat_id)].append({
                            "symbol": ticker_to_add,
                            "quantity": quantity,
                            "avg_price": current_price
                        })
                        send_message(chat_id, f"✅ *{ticker_to_add}* portföyünüze eklendi.\n"
                                             f"Adet: {quantity}, Alış fiyatı: {current_price:,.2f}")

                    save_portfolio(chat_id, portfolios[str(chat_id)])
                except ValueError:
                    send_message(chat_id, "Lütfen geçerli bir adet girin.")
                except Exception as e:
                    send_message(chat_id, f"🔔 *{ticker_to_add}* eklenirken hata: {e}")
                continue

            if text.lower() == "/live":
                user_portfolio = portfolios.get(str(chat_id), [])
                if user_portfolio:
                    send_live_visualization(chat_id, user_portfolio)
                else:
                    send_message(chat_id, "Portföyünüz boş. /add <hisse> <adet> ile ekleyebilirsiniz.")
                continue


            if text.lower().startswith("/remove "):
                ticker_to_remove = text[8:].strip().upper()
                
                current_portfolio = load_portfolios().get(str(chat_id), [])
                
                if not current_portfolio:
                    send_message(chat_id, f"🔔 *{ticker_to_remove}* portföyünüzde bulunamadı.")
                    continue
                
                updated_portfolio = [item for item in current_portfolio if item["symbol"] != ticker_to_remove]
                
                if len(updated_portfolio) == len(current_portfolio):
                    send_message(chat_id, f"🔔 *{ticker_to_remove}* portföyünüzde bulunamadı.")
                else:
                    save_portfolio(chat_id, updated_portfolio)
                    send_message(chat_id, f"✅ *{ticker_to_remove}* portföyünüzden çıkarıldı.")
                continue

            if text.lower() == "/portfoy":
                user_portfolio = portfolios.get(str(chat_id), [])
                if user_portfolio:
                    port_text = "*📋 Portföyünüz:*\n"
                    for item in user_portfolio:
                        port_text += f"- {item['symbol']}: {item['quantity']} adet, Ortalama: {item['avg_price']:,.2f}\n"
                else:
                    port_text = "Portföyünüz boş. /add <hisse> <adet> komutuyla portföyünüze hisse ekleyebilirsiniz."
                send_message(chat_id, port_text)
                continue

            if text.lower().startswith("/alert "):
                try:
                    parts = text.split()
                    if len(parts) != 3:
                        send_message(chat_id, "Lütfen doğru formatta girin: /alert HİSSE FİYAT")
                        continue
                    symbol, target_price = parts[1].upper(), parts[2]
                    target_price = float(target_price.replace(",", "."))
                    t, _ = fetch_ticker(symbol)
                    price = t.fast_info.get("lastPrice", None)
                    if price is None:
                        send_message(chat_id, f"🔔 *{symbol}* bulunamadı.")
                        continue
                    save_alert(chat_id, symbol, target_price)
                    send_message(chat_id, f"✅ *{symbol}* için {target_price:,.2f} fiyat alarmı oluşturuldu.")
                except ValueError:
                    send_message(chat_id, "Lütfen geçerli bir fiyat girin.")
                except Exception as e:
                    send_message(chat_id, f"🔔 *{symbol}* için alarm oluşturulurken hata: {e}")
                continue

            if text.lower().startswith("/remove_alert "):
                symbol = text[13:].strip().upper()
                alerts = get_alerts(chat_id)
                if any(alert["symbol"] == symbol for alert in alerts):
                    remove_alert(chat_id, symbol)
                    send_message(chat_id, f"✅ *{symbol}* alarmı silindi.")
                else:
                    send_message(chat_id, f"🔔 *{symbol}* için alarm bulunamadı.")
                continue

            if text.lower() == "/alert_list":
                alerts = get_alerts(chat_id)
                if alerts:
                    msg = "*📋 Aktif Alarmlarınız:*\n\n"
                    for alert in alerts:
                        msg += f"- {alert['symbol']}: {alert['target_price']:,.2f}\n"
                    send_message(chat_id, msg)
                else:
                    send_message(chat_id, "Aktif alarmınız bulunmuyor.")
                continue

            symbol = text.upper()
            if symbol in fon_kodlari:
                fetch_fon_data(symbol, chat_id)
                continue

            t, symbol = fetch_ticker(symbol)
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
                df = df[["code", "title", "type", "published_at", "price_target", "in_model_portfolio"]]
                df["published_at"] = pd.to_datetime(df["published_at"]).dt.strftime("%Y-%m-%d")
                df.columns = ["Hisse Kodu", "Kurum", "Öneri", "Öneri Tarihi", "Fiyat Hedefi", "Model Portföy"]
                df["Model Portföy"] = df["Model Portföy"].replace({True: "Var", False: "Yok"})

                öneri_df = df[df["Hisse Kodu"] == text.upper()].copy()

                if not öneri_df.empty:
                    t, symbol_full = fetch_ticker(text.upper())
                    current_price = t.fast_info.get("lastPrice", None)
                    
                    if current_price:
                        öneri_df.loc[:, "Son Fiyat"] = round(current_price, 2)
                        öneri_df.loc[:, "Getiri Potansiyeli"] = (öneri_df["Fiyat Hedefi"].astype(float) - current_price).round(2)
                        öneri_df.loc[:, "Getiri Potansiyeli (%)"] = (öneri_df["Getiri Potansiyeli"] / current_price * 100).round(2).astype(str) + "%"
                        columns = ["Hisse Kodu", "Kurum", "Öneri", "Öneri Tarihi", "Fiyat Hedefi", "Son Fiyat", 
                                "Getiri Potansiyeli", "Getiri Potansiyeli (%)", "Model Portföy"]
                        öneri_df = öneri_df[columns]
                    else:
                        öneri_df.loc[:, "Son Fiyat"] = "Veri yok"
                        öneri_df.loc[:, "Getiri Potansiyeli"] = "Veri yok"
                        öneri_df.loc[:, "Getiri Potansiyeli (%)"] = "Veri yok"

                    fig, ax = plt.subplots(figsize=(14, len(öneri_df) * 0.6 + 1))
                    ax.axis('tight')
                    ax.axis('off')
                    table = ax.table(cellText=öneri_df.values, colLabels=öneri_df.columns, loc='center', cellLoc='center')
                    table.auto_set_font_size(False)
                    table.set_fontsize(10)
                    table.scale(1.2, 1.1)

                    öneri_image_path = f"oneriler_{text.upper()}.png"
                    plt.tight_layout()
                    plt.grid(False)
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
            plt.grid(False)
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
    print("İlk Excel dosyası indiriliyor...")
    download_excel()

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
    schedule.every(2).minutes.do(check_alerts)
    schedule.every().day.at("12:00").do(download_excel)
    schedule.every().hour.do(check_excel_and_redownload)

    while True:
        schedule.run_pending()
        last_update_id = process_user_requests(last_update_id)
        time.sleep(1)
