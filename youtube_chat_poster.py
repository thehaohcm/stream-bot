# youtube_chat_poster.py
"""
Module xác thực OAuth 2.0 và đăng comment lên YouTube Live Chat.

Cách hoạt động trong môi trường Docker/Linux server (không có browser):
  1. Chạy generate_token.py trên máy Windows (local) để sinh token.json
  2. Copy token.json vào cùng thư mục với file này trên server
  3. Module sẽ tự động đọc token.json, tự refresh khi hết hạn
"""

import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"

_youtube_service = None
_live_chat_id = None


def get_youtube_service():
    """
    Trả về YouTube API service, tự động refresh token.
    Yêu cầu token.json đã được tạo sẵn (bằng generate_token.py).
    """
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"[YouTube Chat] Không tìm thấy '{TOKEN_FILE}'.\n"
            "Hãy chạy 'python generate_token.py' trên máy Windows trước, "
            f"sau đó copy '{TOKEN_FILE}' lên server này."
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Tự động refresh nếu token hết hạn
    if creds.expired and creds.refresh_token:
        print("[YouTube Chat] Token hết hạn — đang refresh...")
        creds.refresh(Request())
        # Lưu lại token mới
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("[YouTube Chat] Token đã được refresh và lưu lại.")

    return build("youtube", "v3", credentials=creds)


def get_live_chat_id(youtube, video_id: str) -> str | None:
    """Lấy liveChatId từ videoId."""
    try:
        response = youtube.videos().list(
            part="liveStreamingDetails",
            id=video_id
        ).execute()

        items = response.get("items", [])
        if not items:
            print(f"[YouTube Chat] Không tìm thấy video ID: {video_id}")
            return None

        live_chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
        if not live_chat_id:
            print("[YouTube Chat] Video không có live chat đang hoạt động.")
            return None

        print(f"[YouTube Chat] Lấy được liveChatId: {live_chat_id}")
        return live_chat_id

    except Exception as e:
        print(f"[YouTube Chat] Lỗi khi lấy liveChatId: {e}")
        return None


def post_live_chat_message(youtube, live_chat_id: str, message: str) -> bool:
    """Đăng một message lên YouTube Live Chat."""
    try:
        # Giới hạn 200 ký tự (YouTube limit cho live chat)
        message = message[:200]

        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": message
                    }
                }
            }
        ).execute()

        print(f"[YouTube Chat] Đã đăng: {message}")
        return True

    except Exception as e:
        print(f"[YouTube Chat] Lỗi khi đăng comment: {e}")
        return False


def init_youtube_chat(video_id: str):
    """
    Khởi tạo service và lấy liveChatId. Gọi 1 lần khi bot start.
    Trả về (youtube_service, live_chat_id) hoặc (None, None) nếu thất bại.
    """
    global _youtube_service, _live_chat_id
    try:
        _youtube_service = get_youtube_service()
        _live_chat_id = get_live_chat_id(_youtube_service, video_id)
        if _live_chat_id:
            print("[YouTube Chat] Khởi tạo thành công. Bot sẽ reply trên live chat.")
        else:
            print("[YouTube Chat] Không lấy được liveChatId — tắt tính năng reply chat.")
        return _youtube_service, _live_chat_id
    except FileNotFoundError as e:
        print(f"[YouTube Chat] CẢNH BÁO: {e}")
        print("[YouTube Chat] Tính năng reply chat bị tắt.")
        return None, None
    except Exception as e:
        print(f"[YouTube Chat] Lỗi khởi tạo: {e}")
        return None, None
