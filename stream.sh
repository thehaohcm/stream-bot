#!/bin/bash

# --- CẤU HÌNH ---
# Thay bằng RTMP URL và Key của bạn (Lấy từ Youtube Studio > Create > Go Live)
# URL thường là: rtmp://a.rtmp.youtube.com/live2
YT_URL="rtmp://a.rtmp.youtube.com/live2"
YT_KEY="thay-key-cua-ban-vao-day" 

# File đầu vào
AUDIO_INPUT="news_audio.mp3"
FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Font mặc định trên linux

# --- LỆNH FFMPEG ---
echo "Bat dau Livestream len Youtube..."

# Giải thích các tham số:
# -f x11grab -i :99 : Quay màn hình ảo
# -stream_loop -1 -i $AUDIO_INPUT : Lặp lại file mp3 vô hạn (để test)
# -vf drawtext... : Vẽ chữ chạy từ file news.txt
# -c:v libx264 : Mã hóa video chuẩn H.264
# -preset veryfast : Ưu tiên tốc độ để nhẹ CPU VPS
# -b:v 3000k : Bitrate 3000kbps (Đủ nét cho 720p)
# -f flv : Định dạng stream RTMP

ffmpeg -y \
    -thread_queue_size 4096 -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i :99 \
    -thread_queue_size 4096 -f concat -safe 0 -stream_loop -1 -i playlist.txt \
    -c:v libx264 -preset veryfast -tune zerolatency -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p -g 60 \
    -c:a aac -b:a 128k -ar 44100 \
    -vf "drawtext=fontfile=font.ttf:textfile=news_display.txt:reload=1:fontcolor=white:fontsize=24:x=10:y=10:box=1:boxcolor=black@0.5:boxborderw=5" \
    -map 0:v -map 1:a \
    -f flv "$YT_URL/$YT_KEY"
