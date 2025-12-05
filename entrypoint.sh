#!/bin/bash

# 1. Khởi động màn hình ảo
echo "[1/3] Starting Xvfb..."
Xvfb :99 -ac -screen 0 1280x720x24 &
sleep 3

# 2. Khởi động Browser (Chạy ngầm &)
echo "[2/3] Starting Browser..."
python3 browser_worker.py &
sleep 5

# 3. Khởi động Twitter Worker (NEW)
echo "[3/4] Starting Twitter News Aggregator..."
python3 twitter_worker.py &

# 3. Tạo file news.txt giả để ffmpeg không lỗi
echo "Bản tin Crypto 24/7 - Cập nhật liên tục từ hệ thống AI..." > news_display.txt

# 4. Chạy Livestream (Chạy chính, không & để giữ container sống)
# Lưu ý: Bạn cần cấp quyền thực thi: chmod +x stream.sh
echo "[3/3] Starting Stream..."
./stream.sh
