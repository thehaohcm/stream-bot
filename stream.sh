#!/bin/bash

# --- CẤU HÌNH ---
# Thay bằng RTMP URL và Key của bạn (Lấy từ Youtube Studio > Create > Go Live)
# URL thường là: rtmp://a.rtmp.youtube.com/live2
YT_URL="rtmp://a.rtmp.youtube.com/live2"
YT_KEY="thay-key-cua-ban-vao-day" # <--- QUAN TRỌNG: PASTE KEY CỦA BẠN VÀO ĐÂY

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
    -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i :99 \
    -stream_loop -1 -re -i "$AUDIO_INPUT" \
    -c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 60 \
    -c:a aac -b:a 128k -ar 44100 \
    -vf "drawtext=fontfile=$FONT_PATH:textfile=news.txt:y=h-line_h-10:x=w-(t*100):fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5" \
    -f flv "$YT_URL/$YT_KEY"
