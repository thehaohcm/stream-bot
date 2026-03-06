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

# Tạo 1 đoạn audio chào mừng ban đầu thay vì im lặng
echo "[Init] Creating welcome audio..."
python3 -c "import asyncio, tts_worker; asyncio.run(tts_worker.text_to_speech_smart('Chào mừng các bạn đến với luồng trực tiếp. Hãy để lại bình luận để trò chuyện với mình nhé.'))"

# Khởi động Audio Mixer (Tạo named pipe và stream audio liên tục để không crash FFmpeg)
echo "[Audio] Starting Audio Mixer..."
python3 audio_mixer.py &
sleep 2

# 3. Khởi động Browser (Background)
echo "[2/4] Starting Browser..."
python3 browser_worker.py &
sleep 5

# 4. Khởi động Twitter Worker (Background - Vòng lặp lấy tin)
echo "[3/4] Starting Twitter News Aggregator..."
python3 twitter_worker.py &

# Khởi động YouTube AI Worker (Background - Đọc bot chat)
echo "[YouTube AI] Starting YouTube Comment Reader..."
python3 youtube_ai_worker.py &

# 5. Chạy Livestream (Process chính giữ container)
echo "[4/4] Starting Stream..."
# Cấp quyền thực thi cho chắc chắn
chmod +x stream.sh
./stream.sh