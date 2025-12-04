import asyncio
import edge_tts
from gtts import gTTS
import os

# Cấu hình giọng đọc
VOICE_EDGE = "vi-VN-NamMinhNeural" # Giọng đọc tin tức xịn
OUTPUT_FILE = "news_audio.mp3"

async def use_edge_tts(text):
    print(f"[Edge-TTS] Đang thử tạo giọng đọc AI xịn...")
    communicate = edge_tts.Communicate(text, VOICE_EDGE)
    await communicate.save(OUTPUT_FILE)

def use_google_tts(text):
    print(f"[Google-TTS] Edge-TTS bị lỗi (403/Block), chuyển sang Google TTS...")
    # lang='vi' cho tiếng Việt
    tts = gTTS(text=text, lang='vi')
    tts.save(OUTPUT_FILE)

async def text_to_speech_smart(text):
    # Xóa file cũ nếu có
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    try:
        # Ưu tiên 1: Thử dùng Edge TTS (Giọng hay)
        await use_edge_tts(text)
        print(f"[SUCCESS] Đã tạo audio bằng Edge TTS: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[WARNING] Edge TTS thất bại: {e}")
        # Ưu tiên 2: Fallback sang Google TTS (Bao chạy)
        try:
            use_google_tts(text)
            print(f"[SUCCESS] Đã tạo audio bằng Google TTS (Backup): {OUTPUT_FILE}")
        except Exception as e_google:
            print(f"[ERROR] Cả 2 kênh đều lỗi: {e_google}")

# Giả lập tin tức để test
SAMPLE_NEWS = """
Tin nóng thị trường Crypto: Bitcoin vừa chính thức vượt mốc 100 ngàn đô la Mỹ. 
Dòng tiền đang đổ mạnh vào Ethereum. Đây là bản tin thử nghiệm từ hệ thống VPS.
"""

if __name__ == "__main__":
    loop = asyncio.get_event_loop_policy().get_event_loop()
    try:
        loop.run_until_complete(text_to_speech_smart(SAMPLE_NEWS))
    finally:
        loop.close()
