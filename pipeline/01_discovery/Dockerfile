FROM python:3.10-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Copy file requirements vào trước để cài đặt
# (Mẹo: Copy riêng file này giúp Docker cache lại bước cài đặt, build lần sau sẽ cực nhanh)
COPY requirements.txt .

# Cài đặt các thư viện cần thiết
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code và config vào container
COPY . .

# Lệnh mặc định sẽ chạy khi container khởi động
CMD ["python", "main_serper.py"]