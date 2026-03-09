import os
import re
import time
import asyncio
import textwrap
import pytchat
from datetime import datetime
from dotenv import load_dotenv

import tts_worker
import youtube_chat_poster

# Load biến môi trường từ .env
load_dotenv()

# --- CẤU HÌNH ---
VIDEO_ID = os.getenv("YT_VIDEO_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")

DISPLAY_FILE = "news_display.txt"
STOCK_SIGNAL_FILE = "stock_signal.txt"  # File giao tiếp với browser_worker
COOLDOWN_SECONDS = 15 # Chỉ nhận câu hỏi 15s/lần để tránh spam

# Regex nhận dạng mã cổ phiếu: 2-5 ký tự chữ hoa, đứng độc lập trong câu
STOCK_CODE_PATTERN = re.compile(r'\b([A-Z]{2,5})\b')
# Từ khoá gợi ý người dùng đang hỏi về cổ phiếu
STOCK_KEYWORDS = ["cổ phiếu", "cp", "stock", "chart", "biểu đồ", "giá", "mua", "bán", "phân tích"]

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
        system_instruction = "{current time} Bạn là chuyên viên phân tích chứng khoán, crypto, hàng hóa. Hãy trả lời câu hỏi ngắn gọn, tối đa 3 câu và dễ hiểu khi đọc bằng giọng nói."
        
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
    wrapper = textwrap.TextWrapper(width=50)

    display_content = f"{username} hỏi:\n"
    for line in wrapper.wrap(question):
        display_content += f"{line}\n"
        
    display_content += f"\nTrả lời:\n"
    for line in wrapper.wrap(answer):
        display_content += f"{line}\n"
        
    return display_content

def update_display_file(content):
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

async def clear_display_after_delay(delay: int = 60):
    """Xóa nội dung file hiển thị sau `delay` giây."""
    await asyncio.sleep(delay)
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write("")
    print(f"[Display] Đã xóa màn hình sau {delay}s.")

def detect_stock_code(message: str):
    """Trả về mã cổ phiếu nếu message có hỏi về cổ phiếu, ngược lại trả None."""
    msg_lower = message.lower()
    has_stock_keyword = any(kw in msg_lower for kw in STOCK_KEYWORDS)
    matches = STOCK_CODE_PATTERN.findall(message)
    if matches and (has_stock_keyword or len(matches) == 1):
        return matches[0]  # Lấy mã đầu tiên tìm được
    return None

def signal_stock_to_browser(stock_code: str):
    """Ghi mã cổ phiếu vào file để browser_worker đọc và hiển thị chart."""
    with open(STOCK_SIGNAL_FILE, "w", encoding="utf-8") as f:
        f.write(stock_code)
    print(f"[Stock Signal] Đã ghi tín hiệu mã cổ phiếu: {stock_code}")

async def check_chat():
    if not VIDEO_ID:
        print("[YouTube AI] Lỗi: Chưa cấu hình YT_VIDEO_ID trong file .env")
        return

    print(f"[YouTube AI] Bắt đầu lắng nghe chat từ Video ID: {VIDEO_ID}")

    # Khởi tạo YouTube Chat Poster (nếu có token.json)
    yt_service, live_chat_id = youtube_chat_poster.init_youtube_chat(VIDEO_ID)
    
    try:
        chat = pytchat.create(video_id=VIDEO_ID)
        last_answered_time = 0

        print("[YouTube AI] pytchat loop started.")
        while chat.is_alive():
            for c in chat.get().sync_items():
                msg = c.message.strip()
                username = c.author.name

                # Bỏ qua comment của chủ kênh
                if c.author.isChatOwner:
                    print(f"[Chat] Bỏ qua comment của chủ kênh ({username}): {msg}")
                    continue
                
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

                # Kiểm tra có hỏi về mã cổ phiếu không
                stock_code = detect_stock_code(question)
                if stock_code:
                    print(f"[Stock] Phát hiện mã cổ phiếu: {stock_code}")
                    signal_stock_to_browser(stock_code)
                    # Thêm context mã cổ phiếu vào câu hỏi cho AI
                    question = f"Phân tích cổ phiếu {stock_code}: {question}"
                
                # Gọi AI
                answer = generate_ai_response(question)
                print(f"[YouTube AI] Trả lời: {answer}")
                
                # Update screen (tự xóa sau 2 phút)
                screen_text = format_text_for_screen(username, question, answer)
                update_display_file(screen_text)
                asyncio.create_task(clear_display_after_delay(60))
                
                # Update TTS
                audio_text = f"Trong comment có bạn hỏi: {question}. Mình xin trả lời: {answer}"
                await tts_worker.text_to_speech_smart(audio_text)

                # Reply lên YouTube Live Chat
                if yt_service and live_chat_id:
                    reply_text = f"{username}: {answer}"
                    await asyncio.get_event_loop().run_in_executor(
                        None, youtube_chat_poster.post_live_chat_message,
                        yt_service, live_chat_id, reply_text
                    )
            
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
