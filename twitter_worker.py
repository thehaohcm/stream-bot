import feedparser
from deep_translator import GoogleTranslator
import time
import os
import asyncio
from tts_worker import text_to_speech_smart

# Cấu hình đa nguồn
FEEDS = [
    # 1. Nguồn tin tổng hợp (Ổn định nhất - Ưu tiên)
    {
        "name": "Tin Nhanh Crypto", 
        "url": "https://cryptopanic.com/news/rss/",
        "type": "general"
    }
]

LAST_SEEN_LINKS = []
NEWS_FILE = "news.txt"

def get_latest_news():
    print("[News] Dang quet tin moi...")
    latest_news = []
    
    for feed in FEEDS:
        try:
            # Setup request header để tránh bị chặn (quan trọng với Nitter)
            d = feedparser.parse(feed["url"])
            
            if len(d.entries) > 0:
                # Lấy 2 tin mới nhất từ mỗi nguồn
                for i in range(min(2, len(d.entries))):
                    entry = d.entries[i]
                    
                    # Bỏ qua Retweet hoặc Reply (nếu là nguồn Twitter)
                    if feed["type"] == "twitter" and entry.title.startswith("R to @"):
                        continue
                        
                    # Nếu tin chưa từng xử lý
                    if entry.link not in LAST_SEEN_LINKS:
                        print(f"[NEW] Tin moi tu {feed['name']}")
                        
                        # Dịch tiêu đề
                        try:
                            translated = GoogleTranslator(source='auto', target='vi').translate(entry.title)
                        except:
                            translated = entry.title # Fallback nếu lỗi dịch
                        
                        news_item = {
                            "source": feed["name"],
                            "translated": translated
                        }
                        latest_news.append(news_item)
                        LAST_SEEN_LINKS.append(entry.link)
                        
                        # Cache 50 link
                        if len(LAST_SEEN_LINKS) > 50:
                            LAST_SEEN_LINKS.pop(0)

        except Exception as e:
            print(f"[ERROR] Loi nguon {feed['name']}: {e}")

    return latest_news

async def main_loop():
    while True:
        new_items = get_latest_news()
        
        if new_items:
            # Đọc file cũ để nối thêm tin mới (tránh mất tin cũ đang chạy chữ)
            current_ticker = ""
            try:
                with open(NEWS_FILE, "r", encoding="utf-8") as f:
                    current_ticker = f.read()
            except: pass

            full_speak_text = ""
            new_ticker_chunk = ""
            
            for item in new_items:
                # Soạn nội dung đọc
                full_speak_text += f"Tin mới từ {item['source']}: {item['translated']}. "
                # Soạn nội dung chạy chữ
                new_ticker_chunk += f" | [{item['source']}] {item['translated']}"

            # Giới hạn độ dài chạy chữ (chỉ giữ khoảng 1000 ký tự cuối để không bị nặng)
            final_ticker = (current_ticker + new_ticker_chunk)[-2000:]
            
            # 1. Ghi file chạy chữ
            with open(NEWS_FILE, "w", encoding="utf-8") as f:
                f.write(final_ticker)
            
            # 2. Đọc tin mới
            await text_to_speech_smart(full_speak_text)
            
        else:
            print("[News] Khong co tin moi...")
            
        # CryptoPanic update khá nhanh, check mỗi 3 phút
        await asyncio.sleep(180)

if __name__ == "__main__":
    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(main_loop())