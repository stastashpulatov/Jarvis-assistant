"""
Тест воспроизведения через sounddevice.
Берёт уже подтверждённо чистый _diag_cpu.wav и проигрывает его
ТОЧНО так же, как это делает test_rvc.bat (через sd.play + sd.wait).

Если этот файл при таком воспроизведении звучит с искажениями,
хотя сам файл чистый - проблема в sounddevice/аудио-драйвере,
а не в генерации звука или модели.

Запуск:
    rvc_env\\Scripts\\python.exe test_playback.py
"""
import soundfile as sf
import sounddevice as sd
import pathlib

path = pathlib.Path(__file__).parent / "_diag_cpu.wav"

if not path.exists():
    print(f"ERROR: {path} not found. Run diagnose_silero.py first.")
else:
    print("Available audio output devices:")
    print(sd.query_devices())
    print()
    print("Default output device:", sd.default.device)
    print()

    data, sr = sf.read(str(path))
    print(f"File sample rate: {sr} Hz, shape: {data.shape}, dtype: {data.dtype}")
    print()
    print("Playing via sd.play() + sd.wait() (same as test_rvc.bat)...")
    sd.play(data, sr)
    sd.wait()
    print("Done playing.")
