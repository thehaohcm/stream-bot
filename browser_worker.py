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
# TARGET_URL = "https://www.coinglass.com/pro/futures/LiquidationHeatMap"

TARGET_URL = "https://www.usdebtclock.org/world-debt-clock.html"

def start_browser():
    print("Dang khoi dong Chrome...")
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(TARGET_URL)
        print(f"Da mo trang: {TARGET_URL}")
        
        # Giữ trình duyệt luôn mở
        while True:
            time.sleep(60) # Cứ 60s kiểm tra một lần (hoặc reload nếu cần)
            # Có thể thêm logic tự động cuộn trang hoặc chuyển tab tại đây
            
    except Exception as e:
        print(f"Loi Browser: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    start_browser()
