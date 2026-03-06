import os
import time
import asyncio
import textwrap
import pytchat
from datetime import datetime
from dotenv import load_dotenv

import tts_worker

# Load biến môi trường từ .env
load_dotenv()

# --- CẤU HÌNH ---
VIDEO_ID = os.getenv("YT_VIDEO_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")

DISPLAY_FILE = "news_display.txt"
COOLDOWN_SECONDS = 15 # Chỉ nhận câu hỏi 15s/lần để tránh spam

# Khởi tạo API Clients
ai_client = None
USE_GEMINI = False
USE_GROK = False

if GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    ai_client = genai.GenerativeModel('gemini-flash-latest')
    USE_GEMINI = True
    print("[AI Setup] Sử dụng Gemini AI")
elif GROK_API_KEY:
    import openai
    ai_client = openai.OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.x.ai/v1",
    )
    USE_GROK = True
    print("[AI Setup] Sử dụng Grok AI")
else:
    print("[AI Setup] CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY hoặc GROK_API_KEY.")

def generate_ai_response(prompt):
    try:
        system_instruction = "Bạn là trợ lý AI trên livestream. Hãy trả lời câu hỏi ngắn gọn, tối đa 3 câu và dễ hiểu khi đọc bằng giọng nói."
        
        if USE_GEMINI:
            response = ai_client.generate_content(system_instruction + " Câu hỏi: " + prompt)
            return response.text.replace("*", "").strip()
        elif USE_GROK:
            response = ai_client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        else:
            return "Xin lỗi, AI chưa được cài đặt API Key."
    except Exception as e:
        print(f"[AI Error] Lỗi gọi AI: {e}")
        return "Xin lỗi hệ thống AI đang gặp sự cố."

def format_text_for_screen(username, question, answer):
    display_content = f"Q&A: {datetime.now().strftime('%H:%M %d/%m')}\n"
    display_content += "-" * 40 + "\n"
    
    wrapper = textwrap.TextWrapper(width=50)
    
    display_content += f"👤 {username} hỏi:\n"
    for line in wrapper.wrap(question):
        display_content += f"{line}\n"
        
    display_content += f"\n🤖 AI trả lời:\n"
    for line in wrapper.wrap(answer):
        display_content += f"{line}\n"
        
    return display_content

def update_display_file(content):
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

async def check_chat():
    if not VIDEO_ID:
        print("[YouTube AI] Lỗi: Chưa cấu hình YT_VIDEO_ID trong file .env")
        return

    print(f"[YouTube AI] Bắt đầu lắng nghe chat từ Video ID: {VIDEO_ID}")
    
    try:
        chat = pytchat.create(video_id=VIDEO_ID)
        last_answered_time = 0

        print("[YouTube AI] pytchat loop started.")
        while chat.is_alive():
            for c in chat.get().sync_items():
                msg = c.message.strip()
                username = c.author.name
                
                print(f"[Chat] {username}: {msg}")
                
                # Logic: Trả lời tất cả câu hỏi nhưng vẫn giữ cooldown để không bị spam quá nhanh.
                # Cắt từ khoá gọi bot (nếu có) để AI tập trung vào câu hỏi
                question = msg
                for prefix in ["!bot ", "!ai ", "bot, ", "ai, ", "bot ", "ai "]:
                    if msg.lower().startswith(prefix):
                        question = msg[len(prefix):].strip()
                        break
                
                now = time.time()
                if now - last_answered_time < COOLDOWN_SECONDS:
                    print(f"[YouTube AI] Bỏ qua câu hỏi vì đang cooldown ({COOLDOWN_SECONDS}s).")
                    continue
                    
                print(f"[YouTube AI] Đang trả lời {username}: {question}")
                last_answered_time = now
                
                # Gọi AI
                answer = generate_ai_response(question)
                print(f"[YouTube AI] Trả lời: {answer}")
                
                # Update screen
                screen_text = format_text_for_screen(username, question, answer)
                update_display_file(screen_text)
                
                # Update TTS
                audio_text = f"Bạn {username} hỏi: {question}. Khách mời AI xin trả lời: {answer}"
                await tts_worker.text_to_speech_smart(audio_text)
            
            # Nghỉ một chút trước khi lấy chat tiếp theo
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"[YouTube AI] Lỗi vòng lặp chat: {e}")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(check_chat())
            time.sleep(10) # Thử kết nối lại sau 10s nếu đứt
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(10)
