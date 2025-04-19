FROM python:3.12-slim

# Gerekli paketleri kur
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    wget gnupg unzip curl xvfb \
    fonts-liberation libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 \
    libgbm1 libgcc1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 libx11-6 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libxrender1 libxss1 libxtst6 lsb-release xdg-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ortam Değişkenleri
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . /app
WORKDIR /app

# Start script oluştur
RUN echo '#!/bin/bash\n\
Xvfb :99 -screen 0 1920x1080x24 &\n\
python app.py' > /app/start.sh && \
    chmod +x /app/start.sh

# Başlatıcı
CMD ["/app/start.sh"]
