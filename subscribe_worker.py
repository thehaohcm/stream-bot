# subscribe_worker.py
# Mỗi 15 phút: phát TTS nhắc like/subscribe và báo browser_worker hiển thị clip

import asyncio
import time
import os
from datetime import datetime

import tts_worker

# --- CẤU HÌNH ---
REMIND_INTERVAL = 900          # 15 phút
SUBSCRIBE_SIGNAL_FILE = "subscribe_signal.txt"

REMIND_TEXT = (
    "Hãy nhấn like và nhấn nút đăng ký kênh để luôn nhận được tin tức mới nhất. "
    "Xin cảm ơn."
)


def write_subscribe_signal():
    """Ghi file tín hiệu để browser_worker biết hiển thị trang subscribe."""
    with open(SUBSCRIBE_SIGNAL_FILE, "w", encoding="utf-8") as f:
        f.write("show")
    print(f"[Subscribe] Đã ghi tín hiệu subscribe: {SUBSCRIBE_SIGNAL_FILE}")


async def remind_subscribe():
    """Phát TTS nhắc subscribe và gửi tín hiệu đến browser."""
    print(f"\n[Subscribe] Nhắc subscribe lúc {datetime.now().strftime('%H:%M:%S')}...")

    # Gửi tín hiệu browser trước để trang hiển thị cùng lúc với TTS
    write_subscribe_signal()

    # Phát TTS
    await tts_worker.text_to_speech_smart(REMIND_TEXT)
    print("[Subscribe] Đã phát TTS nhắc subscribe.")


async def run():
    """Vòng lặp chính: delay 15 phút trước mỗi lần nhắc."""
    print("[Subscribe Worker] Bắt đầu. Nhắc đầu tiên sau 15 phút...")
    # Không nhắc ngay khi mới khởi động (tránh đụng vào welcome audio)
    await asyncio.sleep(REMIND_INTERVAL)

    while True:
        try:
            await remind_subscribe()
        except Exception as e:
            print(f"[Subscribe] Lỗi vòng lặp: {e}")

        print(f"[Subscribe] Chờ {REMIND_INTERVAL // 60} phút đến lần tiếp theo...")
        await asyncio.sleep(REMIND_INTERVAL)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            print("[Subscribe Worker] Dừng.")
            break
        except Exception as e:
            print(f"[Subscribe Worker] Lỗi không mong đợi: {e}")
            time.sleep(30)
