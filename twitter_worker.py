import feedparser
from deep_translator import GoogleTranslator
import asyncio
import tts_worker
import time
import os
import textwrap
from datetime import datetime

# --- CẤU HÌNH ---
RSS_URL = "https://cryptopanic.com/news/rss/"
MAX_NEWS = 3 # Đọc 3 tin mới nhất thôi cho đỡ dài
CHECK_INTERVAL = 300 # 5 phút (300 giây)
LAST_LINK_FILE = "last_news_link.txt" # File lưu link tin cũ để so sánh
DISPLAY_FILE = "news_display.txt" # File text để hiện lên màn hình

def get_last_processed_link():
    if os.path.exists(LAST_LINK_FILE):
        with open(LAST_LINK_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_last_processed_link(link):
    with open(LAST_LINK_FILE, "w") as f:
        f.write(link)

def format_text_for_screen(text_list):
    """
    Format văn bản để hiển thị đẹp trên màn hình (word wrap)
    """
    display_content = f"UPDATE: {datetime.now().strftime('%H:%M %d/%m')}\n"
    display_content += "-" * 40 + "\n"
    
    wrapper = textwrap.TextWrapper(width=50) # Ngắt dòng nếu quá 50 ký tự
    
    for item in text_list:
        wrapped_lines = wrapper.wrap(text=item)
        for line in wrapped_lines:
            display_content += f"{line}\n"
        display_content += "\n" # Dòng trống giữa các tin
        
    return display_content

def update_display_file(content):
    """Ghi nội dung hiển thị ra file text"""
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

async def process_news():
    print(f"\n[Check] Đang kiểm tra tin mới lúc {datetime.now().strftime('%H:%M:%S')}...")
    
    try:
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            print("[RSS] Không load được tin.")
            return

        # Lấy tin mới nhất để so sánh
        latest_entry = feed.entries[0]
        latest_link = latest_entry.link
        last_link = get_last_processed_link()

        # LOGIC CHECK TIN MỚI
        if latest_link == last_link:
            print("[Skip] Không có tin mới. Ngủ tiếp...")
            return

        print("[Update] 🔥 Phát hiện tin mới! Đang xử lý...")
        
        # --- BẮT ĐẦU XỬ LÝ ---
        translator = GoogleTranslator(source='auto', target='vi')
        full_audio_text = "Cập nhật tin tức Crypto mới nhất. "
        display_list = []

        count = 0
        for entry in feed.entries:
            if count >= MAX_NEWS: break
            
            # Dịch tiêu đề
            try:
                vi_title = translator.translate(entry.title)
                full_audio_text += f"Tin {count+1}: {vi_title}. "
                display_list.append(f"• {vi_title}")
                count += 1
            except:
                continue

        # 1. Cập nhật file hiển thị cho màn hình (news_display.txt)
        screen_text = format_text_for_screen(display_list)
        update_display_file(screen_text)
        print("[File] Đã cập nhật news_display.txt")

        # 2. Tạo Audio (gọi tts_worker)
        await tts_worker.text_to_speech_smart(full_audio_text)

        # 3. Lưu lại link tin mới nhất để lần sau không đọc lại
        save_last_processed_link(latest_link)

    except Exception as e:
        print(f"[Error] Lỗi xử lý: {e}")

if __name__ == "__main__":
    # Tạo file display rỗng nếu chưa có để FFmpeg không lỗi lúc đầu
    if not os.path.exists(DISPLAY_FILE):
        with open(DISPLAY_FILE, "w") as f: f.write("Đang tải dữ liệu...")

    while True:
        try:
            asyncio.run(process_news())
            print(f"--- Chờ {CHECK_INTERVAL} giây ---")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi vòng lặp: {e}")
            time.sleep(60)