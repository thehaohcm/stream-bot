#!/bin/bash

# 0. Thiáº¿t láº­p biáº¿n mÃ´i trÆ°á»ng quan trá»ng
export DISPLAY=:99

# Dá»n dáº¹p cÃ¡c file lock cÅ© náº¿u container bá»‹ restart (trÃ¡nh lá»—i Xvfb already running)
rm -f /tmp/.X99-lock

# 1. Khá»Ÿi Ä‘á»™ng mÃ n hÃ¬nh áº£o Xvfb
echo "[1/4] Starting Xvfb..."
Xvfb :99 -ac -screen 0 1280x720x24 &
sleep 2

# 2. KHá»žI Táº O FILE DUMMY (Quan trá»ng nháº¥t Ä‘á»ƒ FFmpeg khÃ´ng crash)
# Táº¡o file text máº·c Ä‘á»‹nh
echo "Há»‡ thá»‘ng Ä‘ang khá»Ÿi Ä‘á»™ng... Vui lÃ²ng chá» cáº­p nháº­t tin tá»©c..." > news_display.txt

# Táº¡o file audio máº·c Ä‘á»‹nh (1 giÃ¢y im láº·ng) Ä‘á»ƒ FFmpeg cÃ³ cÃ¡i mÃ  Ä‘á»c ngay láº­p tá»©c
# Náº¿u khÃ´ng cÃ³ bÆ°á»›c nÃ y, FFmpeg sáº½ bÃ¡o "No such file" vÃ  sáº­p trÆ°á»›c khi Twitter Worker cháº¡y xong.
echo "[Init] Creating dummy audio..."
ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -q:a 9 -acodec libmp3lame news_audio.mp3 -y

# 3. Khá»Ÿi Ä‘á»™ng Browser (Cháº¡y ngáº§m)
echo "[2/4] Starting Browser..."
python3 browser_worker.py &
sleep 5

# 4. Khá»Ÿi Ä‘á»™ng Twitter Worker (Cháº¡y ngáº§m - VÃ²ng láº·p láº¥y tin)
echo "[3/4] Starting Twitter News Aggregator..."
python3 twitter_worker.py &

# 5. Cháº¡y Livestream (Process chÃ­nh giá»¯ container)
echo "[4/4] Starting Stream..."
# Cáº¥p quyá»n thá»±c thi cho cháº¯c cháº¯n
chmod +x stream.sh
./stream.sh