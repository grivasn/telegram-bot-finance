FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg2 fonts-liberation libxss1 libappindicator3-1 libasound2 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libgtk-3-0 libxshmfence1 libxext6 libxfixes3 libxi6 libxtst6 libwayland-client0 \
    libwayland-cursor0 libwayland-egl1 libdrm2 xdg-utils lsb-release

RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb


ENV CHROME_BIN=/usr/bin/google-chrome


COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


COPY . /app
WORKDIR /app


CMD ["python", "app.py"]
