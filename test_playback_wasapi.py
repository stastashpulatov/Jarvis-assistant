"""
Тест воспроизведения через WASAPI вместо MME.
MME (устройство по умолчанию) плохо работает с нестандартными
sample rate (наш файл 24000 Hz) и может давать характерное
"бульканье"/искажение из-за автоматического ресэмплинга на лету.

WASAPI - современный Windows Audio API, обычно работает чище.

Запуск:
    rvc_env\\Scripts\\python.exe test_playback_wasapi.py
"""
import soundfile as sf
import sounddevice as sd
import pathlib

path = pathlib.Path(__file__).parent / "_diag_cpu.wav"

if not path.exists():
    print(f"ERROR: {path} not found. Run diagnose_silero.py first.")
    raise SystemExit(1)

data, sr = sf.read(str(path))
print(f"File: sample rate {sr} Hz, shape {data.shape}")
print()

# Найдём WASAPI-устройство вывода "Динамики"
devices = sd.query_devices()
wasapi_out = None
for i, d in enumerate(devices):
    if d['max_output_channels'] > 0 and 'WASAPI' in sd.query_hostapis(d['hostapi'])['name']:
        print(f"Found WASAPI output: [{i}] {d['name']}")
        if wasapi_out is None:
            wasapi_out = i

if wasapi_out is None:
    print("No WASAPI output device found, aborting.")
    raise SystemExit(1)

print()
print(f"Playing via WASAPI device [{wasapi_out}] at native file rate ({sr} Hz)...")
try:
    sd.play(data, sr, device=wasapi_out)
    sd.wait()
    print("Done playing (attempt 1: native rate via WASAPI).")
except Exception as e:
    print(f"Attempt 1 FAILED (expected if device doesn't support {sr} Hz natively): {e}")
print()

# Второй вариант: явно ресэмплировать до 48000 Hz перед отправкой на устройство
print("Now trying explicit resample to 48000 Hz via WASAPI...")
import numpy as np
try:
    import librosa
    data_48k = librosa.resample(data.astype(np.float32).T if data.ndim > 1 else data.astype(np.float32),
                                  orig_sr=sr, target_sr=48000)
    if data_48k.ndim > 1:
        data_48k = data_48k.T
    sd.play(data_48k, 48000, device=wasapi_out)
    sd.wait()
    print("Done playing (attempt 2: resampled to 48000 Hz via WASAPI).")
except ImportError:
    print("librosa not available, skipping resample test.")
