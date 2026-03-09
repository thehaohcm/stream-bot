from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
import time
from pathlib import Path

# Cấu hình Chrome
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")  # <--- DÒNG QUAN TRỌNG MỚI THÊM
options.add_argument("--disable-gpu")  # Tắt GPU phần cứng vì VPS không có
options.add_argument("--kiosk")
options.add_argument("--disable-infobars")
options.add_argument("--window-size=1280,720")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# URL mặc định khi không có câu hỏi cổ phiếu
VIETSTOCK_BASE_URL = "https://stockchart.vietstock.vn/"
VIETSTOCK_STOCK_URL = "https://stockchart.vietstock.vn/?stockcode={}"

# URL muốn livestream khi không có tín hiệu cổ phiếu
TARGET_URLS = [
    VIETSTOCK_BASE_URL,
    "https://mihong.vn/gia-vang-trong-nuoc",
    "https://www.binance.com/en/trade/BTC_USDT?type=spot"
]

# File giao tiếp với youtube_ai_worker
STOCK_SIGNAL_FILE = "stock_signal.txt"
# File giao tiếp với subscribe_worker
SUBSCRIBE_SIGNAL_FILE = "subscribe_signal.txt"

# Trang hiển thị nhắc like/subscribe (đường dẫn tuyệt đối)
_HERE = Path(__file__).parent.resolve()
SUBSCRIBE_HTML = _HERE / "media" / "subscribe.html"

# Thời gian giữ chart cổ phiếu trên màn hình (giây) trước khi quay lại vòng lặp
STOCK_DISPLAY_SECONDS = 60
# Thời gian giữ trang subscribe trên màn hình (giây)
SUBSCRIBE_DISPLAY_SECONDS = 15
# Thời gian giữ mỗi URL trong vòng lặp thông thường (giây)
ROTATION_SECONDS = 60


def read_stock_signal():
    """Đọc mã cổ phiếu từ file tín hiệu. Trả về None nếu không có."""
    if not os.path.exists(STOCK_SIGNAL_FILE):
        return None
    try:
        with open(STOCK_SIGNAL_FILE, "r", encoding="utf-8") as f:
            code = f.read().strip()
        return code if code else None
    except Exception:
        return None


def clear_stock_signal():
    """Xoá file tín hiệu sau khi đã xử lý."""
    if os.path.exists(STOCK_SIGNAL_FILE):
        os.remove(STOCK_SIGNAL_FILE)


def read_subscribe_signal() -> bool:
    """Trả về True nếu có tín hiệu subscribe đang chờ."""
    return os.path.exists(SUBSCRIBE_SIGNAL_FILE)


def clear_subscribe_signal():
    """Xoá file tín hiệu subscribe sau khi đã xử lý."""
    if os.path.exists(SUBSCRIBE_SIGNAL_FILE):
        os.remove(SUBSCRIBE_SIGNAL_FILE)


def start_browser():
    print("Dang khoi dong Chrome...")
    driver = webdriver.Chrome(options=options)

    current_index = 0
    last_url = None

    try:
        while True:
            # --- Ưu tiên cao nhất: tín hiệu subscribe ---
            if read_subscribe_signal():
                clear_subscribe_signal()
                subscribe_url = SUBSCRIBE_HTML.as_uri()  # file:///absolute/path/media/subscribe.html
                print(f"[Subscribe Signal] Hiển thị trang subscribe: {subscribe_url}")
                driver.get(subscribe_url)
                last_url = subscribe_url

                # Giữ trang subscribe trong SUBSCRIBE_DISPLAY_SECONDS, vẫn kiểm tra tín hiệu mỗi 2s
                elapsed = 0
                while elapsed < SUBSCRIBE_DISPLAY_SECONDS:
                    time.sleep(2)
                    elapsed += 2

                # Quay lại URL thường
                target = TARGET_URLS[current_index]
                driver.get(target)
                last_url = target
                print(f"[Browser] Hết thời gian subscribe, quay về {target}")
                continue  # Tiếp tục vòng lặp chính ngay (không bước current_index)

            # --- Ưu tiên: tín hiệu cổ phiếu ---
            stock_code = read_stock_signal()
            if stock_code:
                clear_stock_signal()
                stock_url = VIETSTOCK_STOCK_URL.format(stock_code)
                print(f"[Stock Signal] Hiển thị chart cổ phiếu: {stock_code} -> {stock_url}")
                if last_url != stock_url:
                    driver.get(stock_url)
                    last_url = stock_url

                # Giữ chart trong STOCK_DISPLAY_SECONDS, nhưng vẫn kiểm tra tín hiệu mới mỗi 2s
                elapsed = 0
                while elapsed < STOCK_DISPLAY_SECONDS:
                    time.sleep(2)
                    elapsed += 2
                    new_signal = read_stock_signal()
                    if new_signal and new_signal != stock_code:
                        # Có mã mới -> xử lý ngay
                        stock_code = new_signal
                        clear_stock_signal()
                        stock_url = VIETSTOCK_STOCK_URL.format(stock_code)
                        print(f"[Stock Signal] Cập nhật chart mới: {stock_code} -> {stock_url}")
                        driver.get(stock_url)
                        last_url = stock_url
                        elapsed = 0  # reset timer

                # Sau khi hết thời gian hiển thị, quay lại Vietstock mặc định
                print(f"[Browser] Hết thời gian hiển thị chart, quay về {VIETSTOCK_BASE_URL}")
                driver.get(VIETSTOCK_BASE_URL)
                last_url = VIETSTOCK_BASE_URL
                current_index = 0  # reset vòng lặp về đầu
                time.sleep(ROTATION_SECONDS)

            else:
                # --- Vòng lặp URL thông thường ---
                target = TARGET_URLS[current_index]
                if last_url != target:
                    driver.get(target)
                    print(f"Da mo trang: {target}")
                    last_url = target

                # Giữ trang trong ROTATION_SECONDS, kiểm tra tín hiệu mỗi 2s
                elapsed = 0
                while elapsed < ROTATION_SECONDS:
                    time.sleep(2)
                    elapsed += 2
                    if read_stock_signal():
                        break  # Thoát sớm để xử lý tín hiệu

                current_index = (current_index + 1) % len(TARGET_URLS)

    except Exception as e:
        print(f"Loi Browser: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    start_browser()
