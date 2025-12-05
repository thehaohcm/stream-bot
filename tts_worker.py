# tts_worker.py
import asyncio
import edge_tts
from gtts import gTTS
import os
import shutil

# --- CẤU HÌNH ---
VOICE_EDGE = "vi-VN-NamMinhNeural" 
TEMP_FILE = "news_audio_temp.mp3"
FINAL_FILE = "news_audio.mp3"

async def _use_edge_tts(text, output_file):
    print(f"[Edge-TTS] Đang tạo audio...")
    communicate = edge_tts.Communicate(text, VOICE_EDGE)
    await communicate.save(output_file)

def _use_google_tts(text, output_file):
    print(f"[Google-TTS] Fallback sang Google...")
    tts = gTTS(text=text, lang='vi')
    tts.save(output_file)

async def text_to_speech_smart(text):
    """
    Hàm này nhận vào một chuỗi văn bản (text) và tạo ra file news_audio.mp3
    """
    # Xóa file tạm cũ
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

    success = False

    # 1. Thử Edge TTS
    try:
        await _use_edge_tts(text, TEMP_FILE)
        success = True
    except Exception as e:
        print(f"[TTS-Warning] Edge-TTS lỗi: {e}")
        # 2. Fallback Google TTS
        try:
            _use_google_tts(text, TEMP_FILE)
            success = True
        except Exception as e_google:
            print(f"[TTS-Error] Google TTS cũng lỗi: {e_google}")

    # 3. Atomic Move
    if success and os.path.exists(TEMP_FILE):
        shutil.move(TEMP_FILE, FINAL_FILE)
        print(f"[TTS-Success] ✅ Đã cập nhật file audio: {FINAL_FILE}")
        return True
    else:
        print("[TTS-Fail] ❌ Không tạo được file audio.")
        return False