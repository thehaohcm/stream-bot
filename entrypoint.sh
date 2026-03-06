#!/bin/bash

# 0. Thiáº¿t láº­p biáº¿n mÃ´i trÆ°á»ng quan trá»ng
export DISPLAY=:99

# Dá»n dáº¹p cÃ¡c file lock cÅ© náº¿u container bá»‹ restart (trÃ¡nh lá»—i Xvfb already running)
rm -f /tmp/.X99-lock

# 1. Khá»Ÿi Ä‘á»™ng mÃ n hÃ¬nh áº£o Xvfb
echo "[1/4] Starting Xvfb..."
Xvfb :99 -ac -screen 0 1280x720x24 &
sleep 2

# Táº¡o file text máº·c Ä‘á»‹nh
echo "Há»‡ thá»‘ng Ä‘ang khá»Ÿi Ä‘á»™ng... Vui lÃ²ng chá»  cáº­p nháº­t tin tá»©c..." > news_display.txt

# Tạo 1 đoạn audio chào mừng ban đầu thay vì im lặng
echo "[Init] Creating welcome audio..."
python3 -c "import asyncio, tts_worker; asyncio.run(tts_worker.text_to_speech_smart('Chào mừng các bạn đến với luồng trực tiếp. Hãy để lại bình luận để trò chuyện với AI nhé.'))"

# Khởi động Audio Mixer (Tạo named pipe và stream audio liên tục để không crash FFmpeg)
echo "[Audio] Starting Audio Mixer..."
python3 audio_mixer.py &
sleep 2

# 3. Khá»Ÿi Ä‘á»™ng Browser (Cháº¡y ngáº§m)
echo "[2/4] Starting Browser..."
python3 browser_worker.py &
sleep 5

# 4. Khởi động Twitter Worker (Chạy ngầm - Vòng lặp lấy tin)
echo "[3/4] Starting Twitter News Aggregator..."
python3 twitter_worker.py &

# Khởi động YouTube AI Worker (Chạy ngầm - Đọc bot chat)
echo "[YouTube AI] Starting YouTube Comment Reader..."
python3 youtube_ai_worker.py &

# 5. Cháº¡y Livestream (Process chÃ­nh giá»¯ container)
echo "[4/4] Starting Stream..."
# Cáº¥p quyá»n thá»±c thi cho cháº¯c cháº¯n
chmod +x stream.sh
./stream.sh