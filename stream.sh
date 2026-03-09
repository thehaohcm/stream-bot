#!/bin/bash

# RTMP destination
YT_URL="rtmp://a.rtmp.youtube.com/live2"
# YT_KEY is injected from .env via: docker run --env-file .env ...
# Kiểm tra xem YT_KEY đã được truyền vào chưa
YT_KEY=""
if [ -z "$YT_KEY" ]; then
    echo "LỖI: YT_KEY không tồn tại. Hãy kiểm tra file .env hoặc Docker config."
    exit 1
fi

# Thời gian hiển thị màn hình chờ thumbnail (giây), mặc định 120 giây
WAITING_DURATION="${WAITING_DURATION:-120}"
THUMBNAIL_PATH="/app/media/thumbnail.jpg"

echo "Bat dau Livestream len Youtube..."

# --- PHASE 1: Màn hình chờ với thumbnail tĩnh ---
if [ -f "$THUMBNAIL_PATH" ]; then
    echo "[Stream] Phat thumbnail man hinh cho trong $WAITING_DURATION giay..."
    ffmpeg -y -loglevel error \
        -loop 1 -i "$THUMBNAIL_PATH" \
        -f lavfi -i anullsrc=r=44100:cl=stereo \
        -c:v libx264 -preset veryfast -tune zerolatency -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p -g 60 \
        -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
        -c:a aac -b:a 128k -ar 44100 \
        -t "$WAITING_DURATION" \
        -f flv "$YT_URL/$YT_KEY"
    echo "[Stream] Man hinh cho ket thuc, chuyen sang stream chinh..."
else
    echo "[Stream] Khong tim thay thumbnail ($THUMBNAIL_PATH), bo qua man hinh cho."
fi

# --- PHASE 2: Stream chinh (vong lap tu dong ket noi lai) ---
while true; do
    echo "[Stream] Starting FFmpeg..."
    ffmpeg -y -loglevel error \
        -thread_queue_size 4096 -probesize 42M -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i :99 \
        -thread_queue_size 4096 -f s16le -ar 44100 -ac 2 -i /app/audio_pipe \
        -c:v libx264 -preset veryfast -tune zerolatency -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p -g 60 \
        -c:a aac -b:a 128k -ar 44100 \
        -vf "drawtext=fontfile=font.ttf:textfile=news_display.txt:reload=1:fontcolor=white:fontsize=24:x=10:y=10:box=1:boxcolor=black@0.5:boxborderw=5" \
        -map 0:v -map 1:a \
        -f flv "$YT_URL/$YT_KEY"

    echo "[Stream] FFmpeg stopped (exit $?). Restarting in 5 seconds..."
    sleep 5
done