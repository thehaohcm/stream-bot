"""
Script này chạy 1 lần trên máy Windows (có browser) để tạo token.json.
Sau đó copy token.json lên Linux server / Docker volume.

Cách dùng:
  python generate_token.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

def main():
    print("[OAuth] Đang mở trình duyệt để xác thực...")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    # Mở browser tự động trên máy local
    creds = flow.run_local_server(port=0)

    # Lưu token vào file
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"[OAuth] Token đã được lưu vào '{TOKEN_FILE}'")
    print(f"[OAuth] Copy file '{TOKEN_FILE}' lên Linux server / vào Docker volume của bạn.")

if __name__ == "__main__":
    main()
