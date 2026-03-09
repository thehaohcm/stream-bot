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
CTA_SIGNAL_FILE = "cta_signal.txt"

REMIND_SUBSCRIBE_TEXT = (
    "Hãy nhấn like và nhấn nút đăng ký kênh để luôn nhận được tin tức mới nhất từ hệ thống AI của chúng tôi. "
    "Xin cảm ơn."
)

REMIND_CTA_TEXT = (
    "Hệ thống vừa phát hiện nhiều cơ hội đầu tư hấp dẫn. "
    "Hãy quét ngay mã quy mờ trên màn hình để tham gia nhóm Da Lô nhận tín hiệu giao dịch sớm nhất. "
    "Quét mã ngay kẻo lỡ cơ hội."
)

is_subscribe_next = True


def write_signal(signal_file):
    """Ghi file tín hiệu để browser_worker biết hiển thị trang tương ứng."""
    with open(signal_file, "w", encoding="utf-8") as f:
        f.write("show")
    print(f"[Marketing] Đã ghi tín hiệu: {signal_file}")


async def remind_marketing():
    """Phát TTS nhắc nhở và gửi tín hiệu đến browser xen kẽ subscribe/CTA."""
    global is_subscribe_next
    
    print(f"\n[Marketing] Khởi chạy luồng nhắc nhở lúc {datetime.now().strftime('%H:%M:%S')}...")

    if is_subscribe_next:
        write_signal(SUBSCRIBE_SIGNAL_FILE)
        tts_text = REMIND_SUBSCRIBE_TEXT
    else:
        write_signal(CTA_SIGNAL_FILE)
        tts_text = REMIND_CTA_TEXT

    # Đổi trạng thái cho lần sau
    is_subscribe_next = not is_subscribe_next

    # Phát TTS
    await tts_worker.text_to_speech_smart(tts_text)
    print("[Marketing] Đã phát TTS nhắc nhở.")


async def run():
    """Vòng lặp chính: delay 15 phút trước mỗi lần nhắc."""
    print("[Subscribe Worker] Bắt đầu. Nhắc đầu tiên sau 15 phút...")
    # Không nhắc ngay khi mới khởi động (tránh đụng vào welcome audio)
    await asyncio.sleep(REMIND_INTERVAL)

    while True:
        try:
            await remind_marketing()
        except Exception as e:
            print(f"[Marketing] Lỗi vòng lặp: {e}")

        print(f"[Marketing] Chờ {REMIND_INTERVAL // 60} phút đến lần tiếp theo...")
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
