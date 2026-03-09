import os
import re
import time
import asyncio
import requests
import textwrap
import pytchat
import json
from datetime import datetime
from dotenv import load_dotenv

import tts_worker
import youtube_chat_poster

# Load biến môi trường từ .env
load_dotenv()

# --- CẤU HÌNH ---
VIDEO_ID = os.getenv("YT_VIDEO_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CLIENT_URL = "https://api.groq.com/openai/v1/chat/completions"

DISPLAY_FILE = "news_display.txt"
STOCK_SIGNAL_FILE = "stock_signal.txt"  # File giao tiếp với browser_worker
COOLDOWN_SECONDS = 15 # Chỉ nhận câu hỏi 15s/lần để tránh spam

# Regex nhận dạng mã cổ phiếu: 2-5 ký tự chữ hoa, đứng độc lập trong câu
STOCK_CODE_PATTERN = re.compile(r'\b([A-Z]{2,5})\b')
# Từ khoá gợi ý người dùng đang hỏi về cổ phiếu
STOCK_KEYWORDS = ["cổ phiếu", "cp", "stock", "chart", "biểu đồ", "giá", "mua", "bán", "phân tích"]

POLL_SIGNAL_FILE = "poll_signal.txt"
POLL_DATA_FILE = "poll_data.json"

if GROQ_API_KEY:
    print("[AI Setup] Sử dụng Groq AI")
else:
    print("[AI Setup] CẢNH BÁO: Chưa cấu hình GROQ_API_KEY.")

def generate_ai_response(prompt):
    if not GROQ_API_KEY:
        return "Xin lỗi, AI chưa được cài đặt API Key."

    try:
        system_instruction = f"Bạn là chuyên viên phân tích chứng khoán, crypto, hàng hóa. Hãy trả lời câu hỏi ngắn gọn, tối đa 3 câu và dễ hiểu khi đọc bằng giọng nói."
        
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
            "temperature": 0.7
        }

        response = requests.post(GROQ_CLIENT_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return content.replace("*", "").strip()
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

def reset_poll():
    """Tạo file tín hiệu poll và reset dữ liệu json cho biểu quyết mới."""
    data = {"1": 0, "2": 0, "total": 0}
    with open(POLL_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    with open(POLL_SIGNAL_FILE, "w", encoding="utf-8") as f:
        f.write("show")
    print("[Poll Signal] Đã kích hoạt biểu quyết mới!")

def update_poll(vote: str):
    """Cập nhật dữ liệu biểu quyết nếu tuỳ chọn hợp lệ."""
    if not os.path.exists(POLL_DATA_FILE):
        return
        
    try:
        with open(POLL_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if vote in data:
            data[vote] += 1
            data["total"] += 1
            with open(POLL_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"[Poll] Đã nhận được 1 lượt bình chọn cho phương án {vote}.")
    except Exception as e:
        print(f"[Poll Error] {e}")

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

                # Bỏ qua comment của chủ kênh (hoặc xử lý lệnh admin)
                if c.author.isChatOwner:
                    if msg.lower() == "!poll":
                        reset_poll()
                        continue
                    print(f"[Chat] Bỏ qua comment của chủ kênh ({username}): {msg}")
                    continue
                
                print(f"[Chat] {username}: {msg}")
                
                # Check nếu tin nhắn chỉ chứa số, có thể là vote biểu quyết
                if msg.strip() in ["1", "2"] and os.path.exists(POLL_SIGNAL_FILE):
                    update_poll(msg.strip())
                    continue
                
                # Xử lý bỏ qua các msg chỉ thuần số (VD: 1, 2, 3...) bất kể lúc nào
                if msg.strip().isdigit():
                    continue

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
                    question_for_ai = f"Phân tích cổ phiếu {stock_code}: {question}"
                    wait_audio_text = f"Chào {username}, hệ thống đang hiển thị biểu đồ và phân tích mã {stock_code}, bạn đợi một chút nhé."
                else:
                    question_for_ai = question
                    wait_audio_text = f"Chào {username}, hệ thống đang tải câu trả lời, bạn đợi một chút nhé."
                
                # Tạm hiển thị câu hỏi lên màn hình ngay lập tức trong lúc chờ AI phân tích
                waiting_text = format_text_for_screen(username, question, "AI đang phân tích dữ liệu, vui lòng đợi một chút...")
                update_display_file(waiting_text)
                
                # Phát âm thanh phản hồi ngay lập tức
                await tts_worker.text_to_speech_smart(wait_audio_text)

                # Gọi AI (quá trình này mất vài giây) - dùng executor để không block vòng lặp async
                loop = asyncio.get_event_loop()
                answer = await loop.run_in_executor(None, generate_ai_response, question_for_ai)
                print(f"[YouTube AI] Trả lời: {answer}")
                
                # Update screen với câu trả lời hoàn chỉnh
                screen_text = format_text_for_screen(username, question, answer)
                update_display_file(screen_text)
                asyncio.create_task(clear_display_after_delay(60))
                
                # Update TTS
                if stock_code:
                    audio_text = f"Xin trả lời về mã {stock_code}. {answer}"
                else:
                    audio_text = f"Xin trả lời câu hỏi của {username}. {answer}"
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
