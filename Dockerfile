FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg \
    fonts-liberation \
    libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libnss3 libxss1 libxtst6 \
    chromium chromium-driver \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "app.py"]
