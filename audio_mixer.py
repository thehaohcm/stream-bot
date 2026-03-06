import os
import time

try:
    from pydub import AudioSegment
except ImportError:
    pass

PIPE_PATH = '/app/audio_pipe'

# Create named pipe if it doesn't exist
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

print("[Audio Mixer] Waiting for FFmpeg to open pipe...")
with open(PIPE_PATH, 'wb') as pipe:
    print("[Audio Mixer] Pipe opened! Streaming audio...")
    # 0.1 seconds of silence (44100 Hz, 2 channels, 2 bytes per sample = 17640 bytes)
    chunk_size = int(44100 * 2 * 2 * 0.1)
    silence = b'\x00' * chunk_size
    
    while True:
        if os.path.exists('news_audio.mp3'):
            try:
                # Wait briefly to ensure another process has finished writing to the file
                time.sleep(0.5) 
                
                print("[Audio Mixer] Playing new audio: news_audio.mp3")
                audio = AudioSegment.from_mp3('news_audio.mp3')
                # Resample to strictly match what FFmpeg expects from the pipe
                audio = audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                
                raw = audio.raw_data
                # Write in chunks 
                for i in range(0, len(raw), chunk_size):
                    pipe.write(raw[i:i+chunk_size])
                    pipe.flush()
                
                os.remove('news_audio.mp3')
                print("[Audio Mixer] Played and deleted news_audio.mp3")
                continue
            except Exception as e:
                print(f"[Audio Mixer] Warning / Error playing audio: {e}")
                if os.path.exists('news_audio.mp3'):
                    os.rename('news_audio.mp3', 'news_audio_bad.mp3')
                    
        try:
            # Continuously stream silence so the FFmpeg stream doesn't stall
            pipe.write(silence)
            pipe.flush()
        except BrokenPipeError:
            print("[Audio Mixer] Pipe broken, FFmpeg stopped reading. Exiting...")
            break
