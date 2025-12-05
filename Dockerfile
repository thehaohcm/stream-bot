# Sử dụng Python 3.10 trên nền Debian Bullseye (nhẹ và ổn định)
FROM python:3.10-slim-bullseye

# 1. Cài đặt các gói hệ thống cần thiết
# - xvfb: Tạo màn hình ảo
# - ffmpeg: Xử lý video/stream
# - chromium: Trình duyệt để hiển thị chart
# - pulseaudio: (Tùy chọn) nếu muốn xử lý âm thanh phức tạp sau này
RUN apt-get update && apt-get install -y \
    xvfb \
    ffmpeg \
    chromium \
    chromium-driver \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Thiết lập biến môi trường
# DISPLAY :99 là cổng màn hình ảo mặc định
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# 3. Setup thư mục làm việc
WORKDIR /app

# 4. Cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN wget -O font.ttf https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf

# 5. Copy source code
COPY . .

# 6. Cấp quyền chạy cho script khởi động
RUN chmod +x entrypoint.sh

# 7. Lệnh chạy mặc định
ENTRYPOINT ["./entrypoint.sh"]
