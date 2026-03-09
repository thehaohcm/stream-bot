import asyncio
import feedparser
import requests
from bs4 import BeautifulSoup
import tts_worker
import time
import os
import re
import random
import textwrap
import threading
from datetime import datetime

# --- CẤU HÌNH ---
# Cặp (channel_name, danh sách RSS mirror URL để thử lần lượt)
CHANNELS = [
    {
        "name": "vnwallstreet",
        "rss_mirrors": [
            "https://rsshub.app/telegram/channel/vnwallstreet",
            "https://rss.shab.fun/telegram/channel/vnwallstreet",
            "https://rsshub.feeded.xyz/telegram/channel/vnwallstreet",
            "https://rsshub.rssforever.com/telegram/channel/vnwallstreet",
        ],
        "telegram_url": "https://t.me/s/vnwallstreet",
    },
    {
        "name": "tintucvnws",
        "rss_mirrors": [
            "https://rsshub.app/telegram/channel/tintucvnws",
            "https://rss.shab.fun/telegram/channel/tintucvnws",
            "https://rsshub.feeded.xyz/telegram/channel/tintucvnws",
            "https://rsshub.rssforever.com/telegram/channel/tintucvnws",
        ],
        "telegram_url": "https://t.me/s/tintucvnws",
    },
]

CHECK_INTERVAL_MIN = 180  # 3 phút
CHECK_INTERVAL_MAX = 300  # 5 phút
LAST_LINKS_FILE = "last_news_links.txt"
DISPLAY_FILE = "news_display.txt"
REQUEST_TIMEOUT = 10  # giây

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
}


# ── Fetch helpers ─────────────────────────────────────────────────────────────

def fetch_via_rss(url: str):
    """Thử fetch RSS từ một mirror. Trả về list (link, title) hoặc None nếu lỗi."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            return None
        entries = []
        for e in feed.entries[:5]:
            link = (getattr(e, "link", "") or getattr(e, "id", "")).strip()
            title = getattr(e, "title", "").strip()
            if link and title:
                entries.append((link, title))
        return entries if entries else None
    except Exception as e:
        print(f"    [mirror] {url} → lỗi: {type(e).__name__}: {e}")
        return None


def fetch_via_telegram_web(telegram_url: str):
    """Fallback: scrape trang t.me/s/<channel> trực tiếp."""
    try:
        resp = requests.get(telegram_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        entries = []
        for msg_div in soup.select(".tgme_widget_message")[:5]:
            # Lấy link định danh bài
            link_tag = msg_div.get("data-post") or ""
            if link_tag:
                link = f"https://t.me/{link_tag}"
            else:
                a = msg_div.select_one("a.tgme_widget_message_date")
                link = a["href"] if a else ""

            text_div = msg_div.select_one(".tgme_widget_message_text")
            title = text_div.get_text(" ", strip=True)[:200] if text_div else ""

            if link and title:
                entries.append((link, title))
        return entries if entries else None
    except Exception as e:
        print(f"    [t.me scrape] {telegram_url} → lỗi: {type(e).__name__}: {e}")
        return None


def get_entries_for_channel(channel: dict):
    """Thử lần lượt các RSS mirror, fallback sang t.me scrape."""
    for mirror in channel["rss_mirrors"]:
        print(f"  [Try RSS] {mirror}")
        entries = fetch_via_rss(mirror)
        if entries:
            print(f"  [OK] Lấy được {len(entries)} entries từ {mirror}")
            return entries

    # Tất cả mirror hỏng → thử t.me
    print(f"  [Fallback] Thử scrape {channel['telegram_url']}")
    entries = fetch_via_telegram_web(channel["telegram_url"])
    if entries:
        print(f"  [OK] Scrape được {len(entries)} entries từ t.me")
    return entries


# ── Display helpers ───────────────────────────────────────────────────────────

def load_last_links():
    result = {}
    if os.path.exists(LAST_LINKS_FILE):
        with open(LAST_LINKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    key, link = line.split("|", 1)
                    result[key] = link
    return result


def save_last_links(links_dict):
    with open(LAST_LINKS_FILE, "w", encoding="utf-8") as f:
        for key, link in links_dict.items():
            f.write(f"{key}|{link}\n")


def update_display_file(content):
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def _clear_display_after_delay(delay: int = 60):
    time.sleep(delay)
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write("")
    print(f"[Display] Đã xóa màn hình sau {delay}s.")


def schedule_clear_display(delay: int = 60):
    t = threading.Thread(target=_clear_display_after_delay, args=(delay,), daemon=True)
    t.start()


# ── Text helpers ──────────────────────────────────────────────────────────────

def clean_title(text: str) -> str:
    """Xóa emoji, ký hiệu đặc biệt, và các ký tự gây lỗi FFmpeg drawtext."""
    # Xóa emoji SMP (4-byte: 🔴 🟢 🎉 v.v.)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text, flags=re.UNICODE)
    # Xóa emoji / ký hiệu trong BMP (▫ ▪ ● ○ ◆ ★ v.v.)
    text = re.sub(
        r'[\u2000-\u27FF\u2900-\u2DFF\u3000-\u303F\uFE00-\uFE6F\uFFFC-\uFFFF]',
        '', text, flags=re.UNICODE
    )
    # Xóa % để tránh lỗi 'Stray %' của FFmpeg drawtext
    text = text.replace('%', ' phan tram')
    return ' '.join(text.split())


def for_display(text: str) -> str:
    """Safety net: escape ký tự đặc biệt để FFmpeg drawtext không bị lỗi."""
    return text.replace('%', '%%')


# ── Main loop ─────────────────────────────────────────────────────────────────

async def process_news():
    print(f"\n[Check] Kiểm tra tin mới lúc {datetime.now().strftime('%H:%M:%S')}...")

    last_links = load_last_links()
    updated_links = dict(last_links)
    new_titles = []

    for channel in CHANNELS:
        name = channel["name"]
        print(f"\n[Channel] @{name}")
        entries = get_entries_for_channel(channel)

        if not entries:
            print(f"  [Skip] Không lấy được dữ liệu cho @{name}")
            continue

        latest_link, latest_title = entries[0]
        last_link = last_links.get(name, "")

        print(f"  latest_link = {latest_link!r}")
        print(f"  last_link   = {last_link!r}")

        if latest_link == last_link:
            print(f"  [Skip] Không có tin mới.")
            continue

        # Lấy tối đa 2 tin mới nhất
        for link, title in entries[:2]:
            new_titles.append(title)

        updated_links[name] = latest_link

    if not new_titles:
        print("\n[Skip] Không có tin mới từ tất cả các nguồn.")
        return

    # Làm sạch tiêu đề: xóa emoji, bỏ qua title rỗng sau khi clean
    clean_titles = [ct for t in new_titles if (ct := clean_title(t))]

    # --- Cập nhật hiển thị (tự xóa sau 2 phút) ---
    wrapper = textwrap.TextWrapper(width=55, subsequent_indent='  ')
    display_content = f"BREAKING NEWS: {datetime.now().strftime('%H:%M %d/%m')}\n"
    display_content += "-" * 40 + "\n"
    for title in clean_titles:
        wrapped = wrapper.fill(for_display(title))
        display_content += f"- {wrapped}\n\n"
    update_display_file(display_content)
    schedule_clear_display(60)
    print(f"\n[File] Cập nhật {DISPLAY_FILE} với {len(clean_titles)} tin (tự xóa sau 2 phút)")

    # --- TTS ---
    audio_text = "Tin tức mới nhất. "
    for i, title in enumerate(clean_titles, 1):
        title = title.replace("phan tram", "phần trăm")
        audio_text += f"Tin {i}: {title}. "
    await tts_worker.text_to_speech_smart(audio_text)

    save_last_links(updated_links)
    print("[Save] Đã lưu last_news_links.txt")


if __name__ == "__main__":
    # Reset trạng thái cũ khi khởi động
    if os.path.exists(LAST_LINKS_FILE):
        os.remove(LAST_LINKS_FILE)
        print(f"[Init] Đã xóa {LAST_LINKS_FILE} để reset.")

    if not os.path.exists(DISPLAY_FILE):
        with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
            f.write("Đang tải dữ liệu...")

    while True:
        try:
            asyncio.run(process_news())
            interval = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
            print(f"\n--- Chờ {interval}s ({interval // 60}p{interval % 60}s) ---")
            time.sleep(interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi vòng lặp: {e}")
            time.sleep(60)