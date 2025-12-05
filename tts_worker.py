import asyncio
import edge_tts
from gtts import gTTS
import os
import shutil

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
    # Tên file tạm và file chính thức
    TEMP_FILE = "news_audio_temp.mp3"
    FINAL_FILE = "news_audio.mp3"

    try:
        # 1. Tạo ra file tạm trước (Thay vì ghi thẳng vào news_audio.mp3)
        print(f"[TTS] Dang tao file tam: {TEMP_FILE}...")
        communicate = edge_tts.Communicate(text, VOICE_EDGE)
        await communicate.save(TEMP_FILE)
        
        # 2. Di chuyển file tạm thành file chính (Hành động này là Atomic trên Linux)
        # FFmpeg sẽ không bao giờ đọc phải file lỗi/file rỗng
        shutil.move(TEMP_FILE, FINAL_FILE)
        
        print(f"[SUCCESS] Đã cập nhật file audio mới: {FINAL_FILE}")
        
    except Exception as e:
        print(f"[ERROR] Lỗi TTS: {e}")
        # (Logic fallback sang Google TTS cũng nên dùng file tạm tương tự)

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
