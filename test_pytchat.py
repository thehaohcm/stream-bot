import pytchat
import time
import sys

VIDEO_ID = "W-rG9q6BEMw"

print(f"Connecting to video {VIDEO_ID}...")
try:
    chat = pytchat.create(video_id=VIDEO_ID)
    print(f"Chat created. is_alive: {chat.is_alive()}")
    
    count = 0
    while chat.is_alive() and count < 10:
        print("Checking for items...")
        items = chat.get().sync_items()
        for c in items:
            print(f"[{c.datetime}] {c.author.name}: {c.message}")
        time.sleep(2)
        count += 1
        
    print("Done testing.")
except Exception as e:
    print(f"Error test pytchat: {e}")
