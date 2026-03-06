import os
import time

try:
    from pydub import AudioSegment
except ImportError:
    pass

PIPE_PATH = '/app/audio_pipe'
BG_MUSIC_PATH = 'bg_lofi.mp3'
BG_VOLUME_DB = -10       # Giảm âm lượng nhạc nền (dB âm = nhỏ hơn, thử -15 đến -25)
BG_DUCK_DB   = -20       # Giảm thêm khi có giọng đọc (tổng = BG_VOLUME_DB + BG_DUCK_DB)
SAMPLE_RATE = 44100
CHANNELS = 2
SAMPLE_WIDTH = 2  # bytes (16-bit)
BYTES_PER_SEC = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH  # 176400 bytes/sec
CHUNK_DURATION = 0.1  # seconds
CHUNK_SIZE = int(BYTES_PER_SEC * CHUNK_DURATION)  # 17640 bytes per 0.1s chunk
SILENCE = b'\x00' * CHUNK_SIZE

# Create named pipe if it doesn't exist
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

# Load background music once at startup
bg_audio = None
if os.path.exists(BG_MUSIC_PATH):
    print(f"[Audio Mixer] Loading background music: {BG_MUSIC_PATH}")
    bg_audio = AudioSegment.from_mp3(BG_MUSIC_PATH)
    bg_audio = bg_audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(SAMPLE_WIDTH)
    bg_audio = bg_audio + BG_VOLUME_DB  # Áp dụng giảm âm lượng tổng thể
    bg_raw = bg_audio.raw_data
    bg_len = len(bg_raw)
    print(f"[Audio Mixer] Background music loaded: {bg_len} bytes ({bg_len / BYTES_PER_SEC:.1f}s)")
else:
    bg_raw = None
    bg_len = 0
    print("[Audio Mixer] No background music found, will stream silence.")


def write_realtime(pipe, raw_data):
    """Write PCM bytes to pipe at real-time pace to avoid flooding FFmpeg's buffer."""
    total = len(raw_data)
    written = 0
    while written < total:
        end = min(written + CHUNK_SIZE, total)
        chunk = raw_data[written:end]
        pipe.write(chunk)
        pipe.flush()
        written = end
        time.sleep(CHUNK_DURATION)


def get_bg_chunk(bg_pos, length_bytes):
    """Extract `length_bytes` of background audio from position bg_pos, looping as needed."""
    if not bg_raw:
        return b'\x00' * length_bytes, bg_pos
    result = bytearray()
    pos = bg_pos
    while len(result) < length_bytes:
        remaining = length_bytes - len(result)
        available = bg_len - pos
        take = min(remaining, available)
        result.extend(bg_raw[pos:pos + take])
        pos = (pos + take) % bg_len
    return bytes(result), pos


# Main loop: reconnects pipe whenever FFmpeg restarts
while True:
    print("[Audio Mixer] Waiting for FFmpeg to open pipe...")
    try:
        with open(PIPE_PATH, 'wb') as pipe:
            print("[Audio Mixer] Pipe opened! Streaming audio...")
            bg_pos = 0

            while True:
                try:
                    # --- Voice-over: mix voice with ducked background ---
                    if os.path.exists('news_audio.mp3'):
                        time.sleep(0.3)  # brief wait to ensure file is fully written
                        print("[Audio Mixer] Playing Voice OVER Background: news_audio.mp3")

                        try:
                            voice_audio = AudioSegment.from_mp3('news_audio.mp3')
                            voice_audio = voice_audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(SAMPLE_WIDTH)
                        except Exception as e:
                            print(f"[Audio Mixer] Failed to decode news_audio.mp3: {e}")
                            try:
                                os.rename('news_audio.mp3', 'news_audio_bad.mp3')
                            except Exception:
                                pass
                            continue

                        voice_len = len(voice_audio.raw_data)

                        if bg_raw:
                            bg_chunk_bytes, bg_pos = get_bg_chunk(bg_pos, voice_len)
                            bg_segment = AudioSegment(
                                data=bg_chunk_bytes,
                                sample_width=SAMPLE_WIDTH,
                                frame_rate=SAMPLE_RATE,
                                channels=CHANNELS,
                            )
                            ducked_bg = bg_segment + BG_DUCK_DB  # duck bg during voice-over
                            mixed = ducked_bg.overlay(voice_audio)
                            raw_mix = mixed.raw_data
                        else:
                            raw_mix = voice_audio.raw_data

                        # Write at real-time pace so FFmpeg buffer stays healthy
                        write_realtime(pipe, raw_mix)

                        os.remove('news_audio.mp3')
                        print("[Audio Mixer] Played and deleted news_audio.mp3")
                        continue

                    # --- Background music / silence ---
                    if bg_raw:
                        end_pos = bg_pos + CHUNK_SIZE
                        if end_pos <= bg_len:
                            chunk = bg_raw[bg_pos:end_pos]
                            bg_pos = end_pos
                        else:
                            chunk = bg_raw[bg_pos:] + bg_raw[:end_pos - bg_len]
                            bg_pos = end_pos - bg_len
                        pipe.write(chunk)
                        pipe.flush()
                    else:
                        pipe.write(SILENCE)
                        pipe.flush()

                    time.sleep(CHUNK_DURATION)

                except BrokenPipeError:
                    print("[Audio Mixer] Pipe broken (FFmpeg stopped). Waiting for FFmpeg to restart...")
                    break  # Exit inner loop → re-open pipe
                except Exception as e:
                    print(f"[Audio Mixer] Loop error: {e}")
                    if os.path.exists('news_audio.mp3'):
                        try:
                            os.rename('news_audio.mp3', 'news_audio_bad.mp3')
                        except Exception:
                            pass
                    time.sleep(1)

    except OSError as e:
        print(f"[Audio Mixer] Could not open pipe: {e}. Retrying in 2s...")
        time.sleep(2)
