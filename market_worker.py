# market_worker.py
# Mỗi 30 phút thông báo giá vàng, Bitcoin, VNIndex, S&P500, Nasdaq qua TTS và màn hình

import asyncio
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

import tts_worker

# --- CẤU HÌNH ---
ANNOUNCE_INTERVAL = 1800   # 30 phút
DISPLAY_FILE = "news_display.txt"
DISPLAY_CLEAR_DELAY = 120  # Giữ hiển thị 2 phút

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Fetch helpers ─────────────────────────────────────────────────────────────

def fetch_yfinance(symbol: str) -> float | None:
    """Lấy giá mới nhất của symbol qua yfinance (không cần API key)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        if price and price > 0:
            return float(price)
        return None
    except Exception as e:
        print(f"[Market] yfinance lỗi symbol={symbol}: {e}")
        return None


def fetch_gold_usd() -> float | None:
    """Lấy giá vàng XAU/USD từ yfinance (GC=F = Gold Futures)."""
    return fetch_yfinance("GC=F")


def fetch_bitcoin() -> float | None:
    """Lấy giá Bitcoin BTC/USD từ yfinance."""
    return fetch_yfinance("BTC-USD")


def fetch_sp500() -> float | None:
    """Lấy giá S&P 500 từ yfinance."""
    return fetch_yfinance("^GSPC")


def fetch_nasdaq() -> float | None:
    """Lấy giá Nasdaq 100 từ yfinance."""
    return fetch_yfinance("^NDX")


def fetch_vnindex() -> float | None:
    """
    Lấy giá VNIndex từ:
    1. SSI public REST API (JSON, không cần auth)
    2. Fallback: scrape cafef.vn
    """
    # --- Nguồn 1: SSI REST API ---
    try:
        url = "https://mt.ssi.com.vn/api/market/index?code=VNINDEX"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        if isinstance(data, dict):
            val = (
                data.get("data", {}).get("indexValue")
                or data.get("indexValue")
                or data.get("data", {}).get("CloseIndex")
                or data.get("CloseIndex")
            )
            if val:
                v = float(val)
                if 100 < v < 10000:
                    return v
    except Exception as e:
        print(f"[Market] SSI VNIndex lỗi: {e}")

    # --- Nguồn 2: cafef.vn ---
    try:
        url = "https://cafef.vn/thi-truong-chung-khoan.chn"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for sel in ["#VNINDEX .price", ".vnindex-val", "[data-index='VNINDEX']",
                    ".market-index-value"]:
            el = soup.select_one(sel)
            if el:
                raw = el.get_text(strip=True).replace(",", "").replace(" ", "")
                try:
                    val = float(raw)
                    if 100 < val < 10000:
                        return val
                except ValueError:
                    pass
    except Exception as e:
        print(f"[Market] Scrape VNIndex cafef lỗi: {e}")

    return None


def fetch_gold_vnd() -> float | None:
    """Lấy giá vàng SJC nội địa qua sjc.com.vn XML (html.parser, không cần lxml)."""
    try:
        url = "https://sjc.com.vn/xml/tygiavang.xml"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        # Dùng html.parser — tương thích mà không cần cài lxml
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup.find_all("row"):
            type_val = tag.get("type", "")
            if "1L" in type_val or "1 L" in type_val:
                sell_str = tag.get("sell", "").replace(",", "").strip()
                if sell_str:
                    return float(sell_str)
    except Exception as e:
        print(f"[Market] Scrape giá vàng SJC lỗi: {e}")
    return None


# ── Format helpers ────────────────────────────────────────────────────────────

def fmt_number(value: float, decimals: int = 2) -> str:
    """Format số với dấu phẩy ngàn."""
    if value >= 1_000_000:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def build_announcement(prices: dict) -> tuple[str, str]:
    """
    Trả về (tts_text, display_text) từ dict giá.
    prices keys: gold_usd, gold_vnd, btc, sp500, nasdaq, vnindex
    """
    now = datetime.now().strftime("%H:%M %d/%m/%Y")

    lines_tts = [f"Cập nhật thị trường lúc {now}."]
    lines_display = [f"THỊ TRƯỜNG {now}", "-" * 40]

    def add(label_tts, label_display, value, unit, decimals=2):
        if value is not None:
            val_str = fmt_number(value, decimals)
            lines_tts.append(f"{label_tts}: {val_str} {unit}.")
            lines_display.append(f"{label_display}: {val_str} {unit}")
        else:
            lines_tts.append(f"Không lấy được dữ liệu {label_tts}.")
            lines_display.append(f"{label_display}: --")

    add("Vàng thế giới", "XAU/USD", prices.get("gold_usd"), "đô la mỗi ounce", 2)
    add("Vàng SJC trong nước", "SJC", prices.get("gold_vnd"), "nghìn đồng mỗi lượng", 0)
    add("Bitcoin", "BTC/USD", prices.get("btc"), "đô la", 0)
    add("V N Index", "VNIndex", prices.get("vnindex"), "điểm", 2)
    add("S và P 500", "S&P500", prices.get("sp500"), "điểm", 2)
    add("Nasdaq 100", "Nasdaq", prices.get("nasdaq"), "điểm", 2)

    tts_text = " ".join(lines_tts)
    display_text = "\n".join(lines_display) + "\n"
    return tts_text, display_text


# ── Worker ────────────────────────────────────────────────────────────────────

def update_display_file(content: str):
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        f.write(content)


async def announce_market():
    """Lấy giá và thông báo qua TTS + màn hình."""
    print(f"\n[Market] Cập nhật giá thị trường lúc {datetime.now().strftime('%H:%M:%S')}...")

    prices = {
        "gold_usd": fetch_gold_usd(),
        "gold_vnd": fetch_gold_vnd(),
        "btc": fetch_bitcoin(),
        "vnindex": fetch_vnindex(),
        "sp500": fetch_sp500(),
        "nasdaq": fetch_nasdaq(),
    }

    for k, v in prices.items():
        print(f"  {k}: {v}")

    tts_text, display_text = build_announcement(prices)
    print(f"[Market] TTS: {tts_text}")

    # Cập nhật màn hình
    update_display_file(display_text)

    # Tạo audio TTS
    await tts_worker.text_to_speech_smart(tts_text)

    # Tự xóa màn hình sau delay
    await asyncio.sleep(DISPLAY_CLEAR_DELAY)
    update_display_file("")
    print(f"[Market] Đã xóa màn hình sau {DISPLAY_CLEAR_DELAY}s.")


async def run():
    """Vòng lặp chính: thông báo ngay khi khởi động, sau đó mỗi 30 phút."""
    print("[Market Worker] Bắt đầu...")
    while True:
        try:
            await announce_market()
        except Exception as e:
            print(f"[Market] Lỗi vòng lặp: {e}")

        print(f"[Market] Chờ {ANNOUNCE_INTERVAL // 60} phút đến lần tiếp theo...")
        await asyncio.sleep(ANNOUNCE_INTERVAL)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            print("[Market Worker] Dừng.")
            break
        except Exception as e:
            print(f"[Market Worker] Lỗi không mong đợi: {e}")
            time.sleep(30)
