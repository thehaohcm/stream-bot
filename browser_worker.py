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
options.add_argument("--disable-notifications")
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
# File giao tiếp với subscribe_worker / cta
SUBSCRIBE_SIGNAL_FILE = "subscribe_signal.txt"
CTA_SIGNAL_FILE = "cta_signal.txt"
# File giao tiếp với yt chat cho poll
POLL_SIGNAL_FILE = "poll_signal.txt"

# Trang hiển thị nhắc like/subscribe (đường dẫn tuyệt đối)
_HERE = Path(__file__).parent.resolve()
SUBSCRIBE_HTML = _HERE / "media" / "subscribe.html"
CTA_HTML = _HERE / "media" / "cta.html"
POLL_HTML = _HERE / "media" / "poll.html"

# Thời gian giữ chart cổ phiếu trên màn hình (giây) trước khi quay lại vòng lặp
STOCK_DISPLAY_SECONDS = 60
# Thời gian giữ trang subscribe/cta trên màn hình (giây)
SUBSCRIBE_DISPLAY_SECONDS = 20
# Thời gian giữ trang poll trên màn hình (giây)
POLL_DISPLAY_SECONDS = 90
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

def read_cta_signal() -> bool:
    return os.path.exists(CTA_SIGNAL_FILE)

def clear_cta_signal():
    if os.path.exists(CTA_SIGNAL_FILE):
        os.remove(CTA_SIGNAL_FILE)
        
def read_poll_signal() -> bool:
    return os.path.exists(POLL_SIGNAL_FILE)

def clear_poll_signal():
    if os.path.exists(POLL_SIGNAL_FILE):
        os.remove(POLL_SIGNAL_FILE)

def check_any_priority_signal():
    """Kiểm tra xem có bất kỳ tín hiệu cần ngắt ngang nào không (sub, cta, poll, stock)."""
    return read_subscribe_signal() or read_cta_signal() or read_poll_signal() or read_stock_signal()

def start_browser():
    print("Dang khoi dong Chrome...")
    driver = webdriver.Chrome(options=options)

    current_index = 0
    last_url = None

    try:
        while True:
            # --- Ưu tiên 1 cao nhất: tín hiệu subscribe ---
            if read_subscribe_signal():
                clear_subscribe_signal()
                subscribe_url = SUBSCRIBE_HTML.as_uri()  # file:///absolute/path/media/subscribe.html
                print(f"[Subscribe Signal] Hiển thị trang subscribe: {subscribe_url}")
                driver.get(subscribe_url)
                last_url = subscribe_url

                # Giữ trang subscribe trong SUBSCRIBE_DISPLAY_SECONDS
                elapsed = 0
                while elapsed < SUBSCRIBE_DISPLAY_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5

                # Xong thời gian subscribe, lập tức quay lại vòng lặp báo lại URL phù hợp
                print(f"[Browser] Hết thời gian subscribe")
                continue

            # --- Ưu tiên 2: tín hiệu CTA ---
            if read_cta_signal():
                clear_cta_signal()
                cta_url = CTA_HTML.as_uri()
                print(f"[CTA Signal] Hiển thị trang CTA: {cta_url}")
                driver.get(cta_url)
                last_url = cta_url

                elapsed = 0
                while elapsed < SUBSCRIBE_DISPLAY_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5

                print(f"[Browser] Hết thời gian CTA")
                continue
                
            # --- Ưu tiên 3: tín hiệu POLL ---
            if read_poll_signal():
                clear_poll_signal()
                poll_url = POLL_HTML.as_uri()
                print(f"[Poll Signal] Hiển thị trang Poll: {poll_url}")
                driver.get(poll_url)
                last_url = poll_url

                elapsed = 0
                # Poll vẫn có thể bị ngắt bởi Subscribe hay CTA (vì quan trọng hơn về mặt doanh thu)
                interrupted = False
                while elapsed < POLL_DISPLAY_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5
                    if read_subscribe_signal() or read_cta_signal():
                        interrupted = True
                        break

                print(f"[Browser] Hết thời gian Poll")
                if interrupted:
                    continue

            # --- Ưu tiên 4: tín hiệu cổ phiếu ---
            stock_code = read_stock_signal()
            if stock_code:
                clear_stock_signal()
                stock_url = VIETSTOCK_STOCK_URL.format(stock_code)
                print(f"[Stock Signal] Hiển thị chart cổ phiếu: {stock_code} -> {stock_url}")
                if last_url != stock_url:
                    driver.get(stock_url)
                    last_url = stock_url

                interrupted = False
                # Giữ chart trong STOCK_DISPLAY_SECONDS, kiểm tra tín hiệu mới mỗi 2s
                elapsed = 0
                while elapsed < STOCK_DISPLAY_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5
                    
                    if read_subscribe_signal() or read_cta_signal() or read_poll_signal():
                        interrupted = True
                        break

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

                if interrupted:
                    continue

                # Sau khi hết thời gian hiển thị, quay lại Vietstock mặc định
                print(f"[Browser] Hết thời gian hiển thị chart, quay về {VIETSTOCK_BASE_URL}")
                driver.get(VIETSTOCK_BASE_URL)
                last_url = VIETSTOCK_BASE_URL
                current_index = 0  # reset vòng lặp về đầu
                
                # Giữ màn hình Vietstock chờ xem có tín hiệu khác không
                elapsed = 0
                while elapsed < ROTATION_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5
                    if check_any_priority_signal():
                        break

            else:
                # --- Vòng lặp URL thông thường ---
                target = TARGET_URLS[current_index]
                if last_url != target:
                    driver.get(target)
                    print(f"Da mo trang: {target}")
                    last_url = target

                # Giữ trang trong ROTATION_SECONDS, kiểm tra tín hiệu mỗi 2s
                elapsed = 0
                interrupted = False
                while elapsed < ROTATION_SECONDS:
                    time.sleep(0.5)
                    elapsed += 0.5
                    if check_any_priority_signal():
                        interrupted = True
                        break

                if not interrupted:
                    current_index = (current_index + 1) % len(TARGET_URLS)

    except Exception as e:
        print(f"Loi Browser: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    start_browser()
