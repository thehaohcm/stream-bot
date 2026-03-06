import os
import time

try:
    from pydub import AudioSegment
except ImportError:
    pass

PIPE_PATH = '/app/audio_pipe'
BG_MUSIC_PATH = 'bg_lofi.mp3'

# Create named pipe if it doesn't exist
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

# Load background music
bg_audio = None
if os.path.exists(BG_MUSIC_PATH):
    print(f"[Audio Mixer] Loading background music: {BG_MUSIC_PATH}")
    bg_audio = AudioSegment.from_mp3(BG_MUSIC_PATH)
    bg_audio = bg_audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)

print("[Audio Mixer] Waiting for FFmpeg to open pipe...")
with open(PIPE_PATH, 'wb') as pipe:
    print("[Audio Mixer] Pipe opened! Streaming audio...")
    chunk_size = int(44100 * 2 * 2 * 0.1) # 0.1s chunks
    silence = b'\x00' * chunk_size
    
    bg_pos = 0 # Track position in background audio
    
    while True:
        try:
            # CHECK FOR NEW AI VOICE AUDIO
            if os.path.exists('news_audio.mp3'):
                time.sleep(0.5) # Wait briefly to ensure another process has finished writing to the file
                
                print("[Audio Mixer] Playing Voice OVER Background: news_audio.mp3")
                voice_audio = AudioSegment.from_mp3('news_audio.mp3')
                voice_audio = voice_audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                
                # Duck background music by 15dB and overlay voice
                if bg_audio:
                    # Extract the chunk of background music corresponding to voice audio length
                    voice_duration_ms = len(voice_audio)
                    bg_chunk_ms = bg_audio[int(bg_pos/44100/4*1000) : int(bg_pos/44100/4*1000) + voice_duration_ms]
                    
                    # If bg_chunk is shorter than voice (end of song), loop it
                    while len(bg_chunk_ms) < voice_duration_ms:
                        bg_chunk_ms += bg_audio[: voice_duration_ms - len(bg_chunk_ms)]
                        
                    # Lower background volume and overlay
                    ducked_bg = bg_chunk_ms - 15  # Reduce volume by 15dB
                    mixed_audio = ducked_bg.overlay(voice_audio)
                    
                    raw_mix = mixed_audio.raw_data
                    
                    # Write the mixed audio
                    for i in range(0, len(raw_mix), chunk_size):
                        pipe.write(raw_mix[i:i+chunk_size])
                        pipe.flush()
                        
                    # Advance background music pointer
                    bg_pos = (bg_pos + len(raw_mix)) % len(bg_audio.raw_data)
                else:
                    # No background music, just play voice
                    raw = voice_audio.raw_data
                    for i in range(0, len(raw), chunk_size):
                        pipe.write(raw[i:i+chunk_size])
                        pipe.flush()
                
                os.remove('news_audio.mp3')
                print("[Audio Mixer] Played and deleted news_audio.mp3")
                continue
                
            # PLAY BACKGROUND MUSIC CONTINUOUSLY
            if bg_audio:
                # Read a chunk of background audio
                raw_bg = bg_audio.raw_data
                end_pos = bg_pos + chunk_size
                
                if end_pos <= len(raw_bg):
                    play_chunk = raw_bg[bg_pos:end_pos]
                    bg_pos = end_pos
                else:
                    # Loop around
                    play_chunk = raw_bg[bg_pos:] + raw_bg[:end_pos - len(raw_bg)]
                    bg_pos = end_pos - len(raw_bg)
                    
                pipe.write(play_chunk)
                pipe.flush()
            else:
                # Fallback to silence if no background music
                pipe.write(silence)
                pipe.flush()
                
            # Sleep slightly to prevent burning 100% CPU on fast pipe writes
            time.sleep(0.09)
            
        except BrokenPipeError:
            print("[Audio Mixer] Pipe broken, FFmpeg stopped reading. Exiting...")
            break
        except Exception as e:
            print(f"[Audio Mixer] Loop Error: {e}")
            if os.path.exists('news_audio.mp3'):
                try: os.rename('news_audio.mp3', 'news_audio_bad.mp3')
                except: pass
            time.sleep(1)
