#!/bin/bash

# --- Cáº¤U HÃŒNH ---
# Thay báº±ng RTMP URL vÃ  Key cá»§a báº¡n (Láº¥y tá»« Youtube Studio > Create > Go Live)
# URL thÆ°á»ng lÃ : rtmp://a.rtmp.youtube.com/live2
YT_URL="rtmp://a.rtmp.youtube.com/live2"
YT_KEY="hx20-zkgz-5zsg-b4ax-ab0e" 

# File Ä‘áº§u vÃ o
AUDIO_INPUT="news_audio.mp3"
FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Font máº·c Ä‘á»‹nh trÃªn linux

# --- Lá»†NH FFMPEG ---
echo "Bat dau Livestream len Youtube..."

# Giáº£i thÃ­ch cÃ¡c tham sá»‘:
# -f x11grab -i :99 : Quay mÃ n hÃ¬nh áº£o
# -stream_loop -1 -i $AUDIO_INPUT : Láº·p láº¡i file mp3 vÃ´ háº¡n (Ä‘á»ƒ test)
# -vf drawtext... : Váº½ chá»¯ cháº¡y tá»« file news.txt
# -c:v libx264 : MÃ£ hÃ³a video chuáº©n H.264
# -preset veryfast : Æ¯u tiÃªn tá»‘c Ä‘á»™ Ä‘á»ƒ nháº¹ CPU VPS
# -b:v 3000k : Bitrate 3000kbps (Äá»§ nÃ©t cho 720p)
# -f flv : Äá»‹nh dáº¡ng stream RTMP

ffmpeg -y \
    -thread_queue_size 4096 -probesize 42M -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i :99 \
    -thread_queue_size 4096 -re -stream_loop -1 -i news_audio.mp3 \
    -c:v libx264 -preset veryfast -tune zerolatency -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p -g 60 \
    -c:a aac -b:a 128k -ar 44100 -async 1 \
    -vf "drawtext=fontfile=font.ttf:textfile=news_display.txt:reload=1:fontcolor=white:fontsize=24:x=10:y=10:box=1:boxcolor=black@0.5:boxborderw=5" \
    -map 0:v -map 1:a \
    -f flv "$YT_URL/$YT_KEY"