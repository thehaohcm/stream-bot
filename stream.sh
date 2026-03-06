#!/bin/bash

# Thay bằng RTMP URL và Key của bạn
# URL thường là: rtmp://a.rtmp.youtube.com/live2
YT_URL="rtmp://a.rtmp.youtube.com/live2"

# File Ä‘áº§u vÃ o
AUDIO_INPUT="news_audio.mp3"
FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Font máº·c Ä‘á»‹nh trÃªn linux

# --- Lá»†NH FFMPEG ---
echo "Bat dau Livestream len Youtube..."

# Giáº£i thÃ­ch cÃ¡c tham sá»‘:
# -f x11grab -i :99 : Quay mÃ n hÃ¬nh áº£o
# -f s16le -ar 44100 -ac 2 -i /app/audio_pipe : Đọc pcm audio liên tục từ Audio Mixer, khắc phục việc mất tiếng hoặc đơ Youtube!
# -c:v libx264 : Mã hóa video chuẩn H.264
# -preset veryfast : Ưu tiên tốc độ
# -b:v 3000k : Bitrate
# -f flv : Định dạng stream RTMP

ffmpeg -y \
    -thread_queue_size 4096 -probesize 42M -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i :99 \
    -f s16le -ar 44100 -ac 2 -i /app/audio_pipe \
    -c:v libx264 -preset veryfast -tune zerolatency -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p -g 60 \
    -c:a aac -b:a 128k -ar 44100 \
    -vf "drawtext=fontfile=font.ttf:textfile=news_display.txt:reload=1:fontcolor=white:fontsize=24:x=10:y=10:box=1:boxcolor=black@0.5:boxborderw=5" \
    -map 0:v -map 1:a \
    -f flv "$YT_URL/$YT_KEY"