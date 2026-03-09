import os
import time
import json
import asyncio
import subprocess
import requests
import schedule
import pytz
from datetime import datetime
from dotenv import load_dotenv

import tts_worker
from youtube_chat_poster import get_youtube_service

# Import getters từ các module hiện có
import market_worker
import rss_worker

load_dotenv()

# --- CẤU HÌNH ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CLIENT_URL = "https://api.groq.com/openai/v1/chat/completions"

DISPLAY_FILE = "news_display.txt"
THUMBNAIL_PATH = "media/thumbnail.jpg"

TZ_VN = pytz.timezone('Asia/Ho_Chi_Minh')

BULL_VOICE = "vi-VN-NamMinhNeural"
BEAR_VOICE = "vi-VN-HoaiMyNeural"

# --- HELPERS ---

def get_current_time_vn():
    return datetime.now(TZ_VN)

async def wait_for_mixer():
    """Chờ file news_audio.mp3 được mixer phát và xóa đi."""
    while os.path.exists("news_audio.mp3") or os.path.exists(tts_worker.TEMP_FILE):
        await asyncio.sleep(0.5)

def build_system_prompt(topic):
    return (
        f"Bạn là hệ thống tạo kịch bản talkshow tài chính chuyên nghiệp. "
        f"Chủ đề hôm nay: {topic}. "
        f"Kịch bản gồm 2 nhân vật: 'Bull' (lạc quan, giọng nam) và 'Bear' (bi quan/thận trọng, giọng nữ). "
        f"Hãy viết một đoạn hội thoại dài mang tính tranh luận chuyên sâu, khoảng 15 đến 20 lượt lời (mỗi lượt 2-3 câu ngắn gọn), "
        f"tập trung vào dữ kiện thực tế được cung cấp, xu hướng tiếp theo và điểm mua/bán an toàn. "
        f"BẮT BUỘC TRẢ VỀ CHUẨN JSON VỚI ĐỊNH DẠNG: "
        f"{{\"dialogue\": [{{\"speaker\": \"Bull\", \"text\": \"...\"}}, {{\"speaker\": \"Bear\", \"text\": \"...\"}}]}}"
    )

def fetch_groq_dialogue(prompt, system_instruction):
    if not GROQ_API_KEY:
        print("[Daily Worker] Lỗi: Chưa có GROQ_API_KEY")
        return []

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }

    print("[Daily Worker] Đang gọi Groq API...")
    try:
        response = requests.post(GROQ_CLIENT_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        parsed = json.loads(content)
        return parsed.get("dialogue", [])
    except Exception as e:
        print(f"[Daily Worker] Error calling Groq: {e}")
        return []

# --- CHƯƠNG TRÌNH SÁNG & CHIỀU ---

async def run_morning_crypto_gold():
    print("[Daily Worker] Bắt đầu chương trình 07:30 (Vàng & Crypto)")
    # Thu thập dữ liệu
    gold_usd = market_worker.fetch_gold_usd()
    btc = market_worker.fetch_bitcoin()
    
    # Gom tin tức
    channels_entries = []
    for c in rss_worker.CHANNELS:
        entries = rss_worker.get_entries_for_channel(c)
        if entries:
            channels_entries.extend([f"- {t}" for url, t in entries[:2]])
            
    news_context = "\n".join(channels_entries) if channels_entries else "Không có tin tức nổi bật."
    
    prompt = (
        f"Giá hiện tại - Vàng: {gold_usd}$/oz, Bitcoin: {btc}$.\n"
        f"Tin tức nóng:\n{news_context}\n\n"
        f"Hãy bắt đầu chương trình 'Bản tin Vàng và Crypto sáng nay'."
    )
    
    dialogue = fetch_groq_dialogue(prompt, build_system_prompt("Cập nhật Vàng và Crypto đầu ngày"))
    if dialogue:
        await generate_and_broadcast("Bản tin Vàng & Crypto", dialogue)

async def run_afternoon_stock():
    print("[Daily Worker] Bắt đầu chương trình 15:00 (Chứng Khoán VN)")
    vnidex = market_worker.fetch_vnindex()
    
    # Lấy API tín hiệu
    potential_stocks = "Không rõ điểm mua/bán."
    try:
        req = requests.get("https://trading-api-dark-sunset-2092.fly.dev/getPotentialSymbols", timeout=10)
        req.raise_for_status()
        st_data = req.json()
        # Chuyển list dict thành text tóm tắt
        st_items = []
        for d in st_data.get("data", [])[:5]: # lấy 5 mã nổi bật
            st_items.append(f"Mã {d.get('symbol', '')}: Entry {d.get('entry_point', '')}, Mục tiêu {d.get('target_1', '')}")
        if st_items:
            potential_stocks = "\n".join(st_items)
    except Exception as e:
        print(f"[Daily Worker] Lỗi lấy API tín hiệu: {e}")

    prompt = (
        f"Chỉ số VNIndex hôm nay: {vnidex}.\n"
        f"Tín hiệu điểm mua tiềm năng: \n{potential_stocks}\n\n"
        f"Hãy bắt đầu chương trình 'Thị trường chứng khoán Việt Nam hôm nay'."
    )
    
    dialogue = fetch_groq_dialogue(prompt, build_system_prompt("Tổng kết Chứng Khoán VN cuối ngày"))
    if dialogue:
        await generate_and_broadcast("Chứng khoán Việt Nam hôm nay", dialogue)

# --- BROADCAST & VOD GENERATION ---

async def generate_and_broadcast(title, dialogue):
    """
    1. Lặp qua đoạn thoại, tạo mp3 & text, phát lên livestream 24/7.
    2. Gom tất cả mp3 thành 1 video VOD.
    """
    print(f"[Daily Worker] Đang phát sóng: {title}")
    
    temp_dir = "temp_vod"
    os.makedirs(temp_dir, exist_ok=True)
    audio_files = []
    
    # File tiêu đề tổng
    header = f"=== {title.upper()} ===\n"
    
    import re
    for idx, line in enumerate(dialogue):
        speaker = line.get("speaker", "Bull")
        text = line.get("text", "")
        print(f"[{speaker}] {text}")
        
        # Phát hiện mã chứng khoán (3 chữ cái in hoa)
        matches = re.findall(r'\b([A-Z]{3})\b', text)
        tts_text = text
        found_stock = None
        for m in matches:
            if m not in ["USD", "BTC", "SJC", "VNI"]:
                if not found_stock:
                    found_stock = m
                # Đọc chậm từng chữ cái của mã cổ phiếu
                spaced = " ".join(list(m))
                tts_text = re.sub(rf'\b{m}\b', spaced, tts_text)
                
        if found_stock:
            with open("stock_signal.txt", "w", encoding="utf-8") as f:
                f.write(found_stock)
            print(f"[Daily Worker] Phát hiện mã cổ phiếu {found_stock}, hiển thị chart lên màn hình.")
        
        # update display
        with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
            f.write(header + f"\n[{speaker}]: \n{text}")
            
        # sinh giọng TTS tạm
        voice = BULL_VOICE if speaker == "Bull" else BEAR_VOICE
        tts_worker.VOICE_EDGE = voice
        
        # Chờ audio_mixer rảnh
        await wait_for_mixer()
        
        # Lưu ra file stream (đã tách code để đọc chậm)
        await tts_worker.text_to_speech_smart(tts_text)
        
        # Đồng thời lưu bản copy cho VOD
        vod_audio = f"{temp_dir}/part_{idx}.mp3"
        import shutil
        if os.path.exists("news_audio.mp3"):
            shutil.copy("news_audio.mp3", vod_audio)
            audio_files.append(vod_audio)
            
        # Thêm chút time giữa các lượt thoại
        await asyncio.sleep(1) 
    
    print("[Daily Worker] Đã phát xong trên luồng Live. Đang render VOD...")
    # xóa màn hình
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write("")
        
    await render_and_upload_vod(title, temp_dir, audio_files)

async def render_and_upload_vod(title, temp_dir, audio_files):
    if not audio_files:
        return
        
    # Tạo danh sách file cho FFmpeg concat
    concat_txt = os.path.join(temp_dir, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for audio in audio_files:
            # ffmpeg concat cần đường dẫn format 'file path'
            f.write(f"file '{os.path.abspath(audio)}'\n")
            
    full_audio = os.path.join(temp_dir, "full_audio.mp3")
    
    # Nối audio
    print(f"[Daily Worker] Nối {len(audio_files)} audio files...")
    cmd_concat = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", full_audio]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Render video
    now_str = datetime.now(TZ_VN).strftime("%d-%m-%Y")
    video_title = f"{title} - {now_str}"
    output_mp4 = os.path.join(temp_dir, "daily_vod.mp4")
    
    print("[Daily Worker] Render Video .mp4...")
    if os.path.exists(THUMBNAIL_PATH):
        # loop ảnh + audio
        cmd_vid = [
            "ffmpeg", "-y", "-loop", "1", "-i", THUMBNAIL_PATH, "-i", full_audio,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-shortest", output_mp4
        ]
        subprocess.run(cmd_vid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_mp4):
            print("[Daily Worker] Render xong, bắt đầu Upload YouTube...")
            upload_to_youtube(video_title, output_mp4)
        else:
            print("[Daily Worker] Lỗi render mp4.")
    else:
        print("[Daily Worker] Không tìm thấy thumbnail để render video.")
        
    # Dọn dẹp
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

def upload_to_youtube(title, filepath):
    """Dùng youtube_chat_poster.get_youtube_service() để upload video!"""
    from googleapiclient.http import MediaFileUpload
    try:
        youtube = get_youtube_service()
        
        request_body = {
            "snippet": {
                "title": title,
                "description": "Chương trình tự động phát hành bởi AI Stream Bot.",
                "tags": ["Chứng Khoán", "Crypto", "Tài Chính", "AI"],
                "categoryId": "27" # Education
            },
            "status": {
                "privacyStatus": "public" # public luôn (hoặc private)
            }
        }
        
        media_file = MediaFileUpload(filepath, chunksize=-1, resumable=True)
        print(f"[Daily VOD] Bắt đầu upload video: {title} ...")
        res = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file
        ).execute()
        
        print(f"[Daily VOD] Upload thành công! Video ID: {res.get('id')}")
    except Exception as e:
        print(f"[Daily VOD] Lỗi upload: {e}")

# --- SCHEDULER ---

def job_wrapper(coroutine):
    asyncio.run(coroutine())

def start_scheduler():
    print("[Daily Worker] Khởi động lập lịch tác vụ tự động (Thứ 2 - Thứ 6)...")
    
    # Lập lịch: chú ý schedule thư viện Python KHÔNG hỗ trợ timezone trực tiếp
    # Cần set time UTC hoặc check tz thủ công. 
    # UTC+7: 07:30 VN = 00:30 UTC. 15:00 VN = 08:00 UTC
    weekdays = [
        schedule.every().monday,
        schedule.every().tuesday,
        schedule.every().wednesday,
        schedule.every().thursday,
        schedule.every().friday
    ]
    
    for day_schedule in weekdays:
        day_schedule.at("00:30").do(job_wrapper, run_morning_crypto_gold)
        day_schedule.at("08:00").do(job_wrapper, run_afternoon_stock)
    
    print("[Daily Worker] Lịch trình được set 00:30 UTC và 08:00 UTC (tương đương 07:30 và 15:00 VN) từ Thứ 2 đến Thứ 6.")
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    start_scheduler()
