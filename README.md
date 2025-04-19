# 📊 Telegram Finans Botu

Bu proje, kullanıcıların Telegram üzerinden **hisse senedi**, **fon** ve **kripto para** verilerini takip etmesini sağlayan kapsamlı bir Python tabanlı Telegram botudur.

## 🚀 Özellikler

- 📈 Anlık hisse fiyatı ve teknik analiz grafikleri  
- 💼 Fon kodu ile detaylı TEFAS verileri ve analiz grafiği  
- 💬 `/add`, `/remove`, `/portfoy` komutları ile kişisel portföy yönetimi  
- 🛎️ `/alert` ve `/remove_alert` komutları ile fiyat alarm sistemi  
- 📥 TEFAS fonlarını Selenium ile otomatik indirme  
- 🧠 Analist önerileri (Fintables API)  
- ⏱️ Zamanlanmış özet mesajlar (09:00, 15:00)  
- ☁️ Supabase ile kullanıcı ve portföy verilerini saklama  

---

## 📁 Kurulum

### 1. Gerekli bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
````

### 2. Ortam Değişkenleri
Proje dizinine .env dosyasını oluşturun ve aşağıdaki değerleri girin:

```bash
TOKEN=telegram_bot_tokeniniz
SUPABASE_URL=https://abc.supabase.co
SUPABASE_KEY=supabase_secret_key
````

### 🖥️ Kullanım
Aşağıdaki komut ile botu başlatabilirsiniz:

```bash
python app.py
````

Bot çalıştırıldığında:

- İlk olarak TEFAS Excel dosyasını indirir

- Her 2 dakikada bir alarm kontrolü yapar

- Her gün saat 09:00 ve 15:00'te piyasa özetini gönderir

- Gelen kullanıcı mesajlarını sürekli dinler ve yanıtlama yapar


### 💬 Komutlar

| Komut              | Açıklama                                                      |
|--------------------|---------------------------------------------------------------|
| `/start`           | Botu başlatır                                                 |
| `/stop`            | Bildirimleri durdurur                                         |
| `/add <Hisse>`     | Portföye hisse ekler                                          |
| `/remove <Hisse>`  | Portföyden hisse çıkarır                                      |
| `/portfoy`         | Portföydeki tüm hisseleri listeler                            |
| `/live`            | Portföydeki hisselerin canlı fiyat ve değişim bilgilerini gösterir |
| `/alert <Hisse> <Fiyat>` | Belirtilen hisse için fiyat alarmı kurar               |
| `/remove_alert <Hisse>`  | Belirtilen hisse alarmını kaldırır                   |
| `/alert_list`      | Aktif alarm listesini gösterir                                |
| `BIMAS`, `TLY` gibi | Direkt sembol yazarak analiz, grafik, öneri bilgisi alınır   |


### 🛠️ Kullanılan Teknolojiler

- Python: Uygulamanın genel yapısı

- Selenium: TEFAS sitesinden fon ve Excel verisi indirme

- Supabase: Kullanıcı veritabanı yönetimi

- Matplotlib: Grafik ve tablo görselleştirme

- yFinance: Hisse verisi çekimi

- BeautifulSoup: TEFAS'tan fon fiyat verisi ayrıştırma

- CloudScraper: Fintables API verisi çekimi

- Telegram Bot API: Mesajlaşma sistemi


### ⚙️ Docker (İsteğe Bağlı)
Bu botu Docker ile dağıtmak isterseniz aşağıdaki Dockerfile kullanılabilir:

```bash
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget unzip curl chromium chromium-driver \
    fonts-liberation libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 \
    libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 libx11-6 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libxrender1 libxss1 libxtst6 xdg-utils xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
````






