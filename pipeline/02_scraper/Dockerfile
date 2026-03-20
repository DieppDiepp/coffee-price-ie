FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết cho Playwright (dùng bởi crawl4ai) trên Linux
RUN apt-get update && apt-get install -y \
    wget gnupg \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy thư mục scraper vào container
COPY requirements.txt .

# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt trình duyệt chromium cho Playwright (được dùng bởi crawl4ai)
RUN playwright install chromium
RUN playwright install-deps chromium
~
COPY . .

# Lệnh chạy mặc định
CMD ["python", "main.py"]