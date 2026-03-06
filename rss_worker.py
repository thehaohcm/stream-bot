import asyncio
import feedparser
import requests
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
CHECK_INTERVAL_MIN = 180  # 3 phút
CHECK_INTERVAL_MAX = 300  # 5 phút
LAST_LINKS_FILE = "last_news_links.txt"
DISPLAY_FILE = "news_display.txt"

# User-Agent giả lập browser để tránh bị block
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def fetch_feed(url: str):
    """Fetch RSS bằng requests (có User-Agent) rồi parse bằng feedparser."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        return feed
    except requests.exceptions.RequestException as e:
        print(f"[RSS] Lỗi network khi fetch {url}: {e}")
        return None
    except Exception as e:
        print(f"[RSS] Lỗi parse {url}: {e}")
        return None


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
    updated_links = dict(last_links)  # copy để cập nhật

    for rss_url in RSS_URLS:
        try:
            feed = fetch_feed(rss_url)
            if feed is None or not feed.entries:
                print(f"[Skip] Không lấy được tin từ: {rss_url}")
                continue

            print(f"[RSS] Lấy được {len(feed.entries)} entries từ {rss_url}")

            latest_entry = feed.entries[0]
            latest_link = (
                getattr(latest_entry, "link", "")
                or getattr(latest_entry, "id", "")
            ).strip()
            last_link = last_links.get(rss_url, "")

            print(f"[RSS] latest_link = {latest_link!r}")
            print(f"[RSS] last_link   = {last_link!r}")

            if latest_link and latest_link == last_link:
                print(f"[Skip] Không có tin mới từ {rss_url}")
                continue

            print(f"[Update] 🔥 Tin mới từ {rss_url}!")

            # Lấy tối đa 2 tin mỗi nguồn
            for entry in feed.entries[:2]:
                title = getattr(entry, "title", "").strip()
                if title:
                    new_titles.append(title)

            # Cập nhật link mới nhất
            if latest_link:
                updated_links[rss_url] = latest_link

        except Exception as e:
            print(f"[Error] Lỗi xử lý {rss_url}: {e} — bỏ qua.")
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
    print(f"[File] Đã cập nhật {DISPLAY_FILE} với {len(new_titles)} tin (sẽ tự xóa sau 2 phút)")

    # --- Đọc to trên livestream ---
    audio_text = "Tin tức mới nhất. "
    for i, title in enumerate(new_titles, 1):
        audio_text += f"Tin {i}: {title}. "

    await tts_worker.text_to_speech_smart(audio_text)

    # --- Lưu lại links sau khi đã phát ---
    save_last_links(updated_links)
    print("[Save] Đã lưu last_news_links.txt")


if __name__ == "__main__":
    # Xóa cache link cũ khi khởi động để đảm bảo đọc tin ngay lập tức
    if os.path.exists(LAST_LINKS_FILE):
        os.remove(LAST_LINKS_FILE)
        print(f"[Init] Đã xóa {LAST_LINKS_FILE} để reset trạng thái.")

    # Tạo file display rỗng nếu chưa có để FFmpeg không lỗi lúc đầu
    if not os.path.exists(DISPLAY_FILE):
        with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
            f.write("Đang tải dữ liệu...")

    while True:
        try:
            asyncio.run(process_news())
            interval = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
            print(f"--- Chờ {interval} giây ({interval // 60} phút {interval % 60} giây) ---")
            time.sleep(interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi vòng lặp: {e}")
            time.sleep(60)