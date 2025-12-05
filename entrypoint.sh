#!/bin/bash

# 0. Thiết lập biến môi trường quan trọng
export DISPLAY=:99

# Dọn dẹp các file lock cũ nếu container bị restart (tránh lỗi Xvfb already running)
rm -f /tmp/.X99-lock

# 1. Khởi động màn hình ảo Xvfb
echo "[1/4] Starting Xvfb..."
Xvfb :99 -ac -screen 0 1280x720x24 &
sleep 2

# 2. KHỞI TẠO FILE DUMMY (Quan trọng nhất để FFmpeg không crash)
# Tạo file text mặc định
echo "Hệ thống đang khởi động... Vui lòng chờ cập nhật tin tức..." > news_display.txt

# Tạo file audio mặc định (1 giây im lặng) để FFmpeg có cái mà đọc ngay lập tức
# Nếu không có bước này, FFmpeg sẽ báo "No such file" và sập trước khi Twitter Worker chạy xong.
echo "[Init] Creating dummy audio..."
ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -q:a 9 -acodec libmp3lame news_audio.mp3 -y

# 3. Khởi động Browser (Chạy ngầm)
echo "[2/4] Starting Browser..."
python3 browser_worker.py &
sleep 5

# 4. Khởi động Twitter Worker (Chạy ngầm - Vòng lặp lấy tin)
echo "[3/4] Starting Twitter News Aggregator..."
python3 twitter_worker.py &

# 5. Chạy Livestream (Process chính giữ container)
echo "[4/4] Starting Stream..."
# Cấp quyền thực thi cho chắc chắn
chmod +x stream.sh
./stream.sh