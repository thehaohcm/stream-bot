import feedparser
import asyncio
import tts_worker
import time
import os
import random
import threading
from datetime import datetime

# --- CẤU HÌNH ---
RSS_URLS = [
    "https://rsshub.rssforever.com/telegram/channel/vnwallstreet",
    "https://rsshub.rssforever.com/telegram/channel/tintucvnws",
]
CHECK_INTERVAL_MIN = 180  # 3 phút (giây)
CHECK_INTERVAL_MAX = 300  # 5 phút (giây)
LAST_LINKS_FILE = "last_news_links.txt"  # Lưu link mới nhất của từng feed
DISPLAY_FILE = "news_display.txt"


def load_last_links():
    """Đọc dict {url: last_link} từ file."""
    result = {}
    if os.path.exists(LAST_LINKS_FILE):
        with open(LAST_LINKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    url, link = line.split("|", 1)
                    result[url] = link
    return result


def save_last_links(links_dict):
    """Ghi dict {url: last_link} ra file."""
    with open(LAST_LINKS_FILE, "w", encoding="utf-8") as f:
        for url, link in links_dict.items():
            f.write(f"{url}|{link}\n")


def update_display_file(content):
    """Ghi nội dung hiển thị ra file text."""
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def _clear_display_after_delay(delay: int = 120):
    """Chạy trong thread riêng: xóa file hiển thị sau `delay` giây."""
    time.sleep(delay)
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write("")
    print(f"[Display] Đã xóa màn hình sau {delay}s.")

def schedule_clear_display(delay: int = 120):
    """Kick off background thread để tự xóa màn hình sau delay giây."""
    t = threading.Thread(target=_clear_display_after_delay, args=(delay,), daemon=True)
    t.start()


async def process_news():
    print(f"\n[Check] Đang kiểm tra tin mới lúc {datetime.now().strftime('%H:%M:%S')}...")

    last_links = load_last_links()
    new_titles = []

    for rss_url in RSS_URLS:
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"[Skip] Không lấy được tin từ {rss_url}")
                continue

            latest_entry = feed.entries[0]
            latest_link = getattr(latest_entry, "link", "") or getattr(latest_entry, "id", "")
            last_link = last_links.get(rss_url, "")

            if latest_link == last_link:
                print(f"[Skip] Không có tin mới từ {rss_url}")
                continue

            print(f"[Update] 🔥 Tin mới từ {rss_url}!")

            # Lấy tin mới nhất (tối đa 2 tin mỗi nguồn)
            for entry in feed.entries[:2]:
                title = getattr(entry, "title", "").strip()
                if title:
                    new_titles.append(title)

            # Cập nhật link mới nhất
            last_links[rss_url] = latest_link

        except Exception as e:
            print(f"[Error] Lỗi đọc RSS {rss_url}: {e} — bỏ qua.")
            continue

    if not new_titles:
        print("[Skip] Không có tin mới từ tất cả các nguồn.")
        return

    # --- Cập nhật hiển thị (tự xóa sau 2 phút) ---
    display_content = f"TIN TỨC: {datetime.now().strftime('%H:%M %d/%m')}\n"
    display_content += "-" * 40 + "\n"
    for title in new_titles:
        display_content += f"• {title}\n\n"
    update_display_file(display_content)
    schedule_clear_display(120)
    print("[File] Đã cập nhật news_display.txt (sẽ tự xóa sau 2 phút)")

    # --- Đọc to trên livestream ---
    audio_text = "Tin tức mới nhất. "
    for i, title in enumerate(new_titles, 1):
        audio_text += f"Tin {i}: {title}. "

    await tts_worker.text_to_speech_smart(audio_text)

    # --- Lưu lại links ---
    save_last_links(last_links)


if __name__ == "__main__":
    # Tạo file display rỗng nếu chưa có để FFmpeg không lỗi lúc đầu
    if not os.path.exists(DISPLAY_FILE):
        with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
            f.write("Đang tải dữ liệu...")

    while True:
        try:
            asyncio.run(process_news())
            interval = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
            print(f"--- Chờ {interval} giây ({interval//60} phút {interval%60} giây) ---")
            time.sleep(interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi vòng lặp: {e}")
            time.sleep(60)