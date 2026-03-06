from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Cấu hình Chrome
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage") # <--- DÒNG QUAN TRỌNG MỚI THÊM
options.add_argument("--disable-gpu") # Tắt GPU phần cứng vì VPS không có
options.add_argument("--kiosk")
options.add_argument("--disable-infobars")
options.add_argument("--window-size=1280,720")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# URL muốn livestream (Bạn có thể đổi thành TradingView hoặc bất kỳ web nào)
# Ví dụ: Bản đồ nhiệt thanh lý của Coinglass (Giao diện tối)
TARGET_URLS = [
    "https://stockchart.vietstock.vn/",
    "https://mihong.vn/gia-vang-trong-nuoc",
    "https://www.binance.com/en/trade/BTC_USDT?type=spot"
]

def start_browser():
    print("Dang khoi dong Chrome...")
    driver = webdriver.Chrome(options=options)
    
    try:
        current_index = 0
        while True:
            target = TARGET_URLS[current_index]
            driver.get(target)
            print(f"Da mo trang: {target}")
            
            # Giữ trang hiện hành trong 60s
            time.sleep(60) 
            
            # Chuyển sang URL tiếp theo
            current_index = (current_index + 1) % len(TARGET_URLS)
            
    except Exception as e:
        print(f"Loi Browser: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    start_browser()
