# twitter_worker.py
import feedparser
from deep_translator import GoogleTranslator
import asyncio
import tts_worker  # Import file tts_worker.py ở trên
import time

# --- CẤU HÌNH ---
RSS_URL = "https://cryptopanic.com/news/rss/"
MAX_NEWS = 5  # Số tin muốn đọc

def get_crypto_news():
    print(f"[RSS] Đang tải tin từ CryptoPanic...")
    try:
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            print("[RSS] Không có tin nào.")
            return None

        # Chuẩn bị nội dung
        full_content = "Chào bạn, đây là điểm tin nhanh thị trường Crypto. "
        translator = GoogleTranslator(source='auto', target='vi')

        count = 0
        for entry in feed.entries:
            if count >= MAX_NEWS: break
            
            title_en = entry.title
            print(f"  - (EN): {title_en}")
            
            # Dịch sang Tiếng Việt
            try:
                title_vi = translator.translate(title_en)
                print(f"    (VI): {title_vi}")
                full_content += f"Tin thứ {count + 1}. {title_vi}. "
                count += 1
            except Exception as e:
                print(f"    [Lỗi dịch]: {e}")
                continue

        full_content += "Cảm ơn bạn đã lắng nghe."
        return full_content

    except Exception as e:
        print(f"[RSS-Error] Lỗi lấy tin: {e}")
        return None

async def main():
    # Bước 1: Lấy nội dung text từ RSS
    news_text = get_crypto_news()

    if news_text:
        # Bước 2: Gọi tts_worker để đọc nội dung đó
        print(f"\n[System] Bắt đầu chuyển văn bản sang giọng nói...")
        await tts_worker.text_to_speech_smart(news_text)
    else:
        print("[System] Không có nội dung để đọc.")

if __name__ == "__main__":
    while True:
        try:
            print("\n--- BẮT ĐẦU CHU KỲ CẬP NHẬT TIN TỨC ---")
            asyncio.run(main()) # Chạy lấy tin và tạo audio
            
            print("Đang chờ 15 phút để cập nhật tin tiếp theo...")
            time.sleep(900) # Ngủ 900 giây (15 phút)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi vòng lặp chính: {e}")
            time.sleep(60) # Lỗi thì chờ 1 phút thử lại