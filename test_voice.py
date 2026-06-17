"""
Финальный тест голоса Джарвиса.
python test_voice.py
"""
import sys, os, pathlib, warnings
warnings.filterwarnings("ignore")
os.chdir(pathlib.Path(__file__).parent)

import torch
import sounddevice as sd

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Находим модель
hub_dir = pathlib.Path(torch.hub.get_dir())
pt_path = None
for d in hub_dir.glob("snakers4_silero*"):
    p = d / "src" / "silero" / "model" / "v4_ru.pt"
    if p.exists():
        pt_path = p
        break
    for pt in d.rglob("v4_ru.pt"):
        pt_path = pt
        break

if not pt_path:
    print("Скачиваю Silero...")
    torch.hub.load("snakers4/silero-models", "silero_tts",
                   language="ru", speaker="v4_ru", trust_repo=True, verbose=False)
    for d in hub_dir.glob("snakers4_silero*"):
        for pt in d.rglob("v4_ru.pt"):
            pt_path = pt
            break

print(f"Модель: {pt_path.name}")

importer = torch.package.PackageImporter(str(pt_path))
model    = importer.load_pickle("tts_models", "model")
print(f"Загружен: {type(model).__name__}, apply_tts={hasattr(model, 'apply_tts')}")

# .to() работает in-place и возвращает None - не переприсваивать
result = model.to(device)
if result is not None:
    model = result

# .eval() у этого класса НЕТ - пропускаем
if hasattr(model, "eval"):
    model.eval()

print(f"Готово на {device}!\n")

# Тест
phrases = [
    ("aidar", "Все системы онлайн, сэр. Джарвис готов к работе."),
    ("aidar", "Открываю браузер Chrome, сэр."),
    ("xenia", "Добрый день, сэр. Чем могу помочь?"),
]

for speaker, text in phrases:
    print(f"[{speaker}]: {text}")
    with torch.no_grad():
        audio = model.apply_tts(text=text, speaker=speaker,
                                sample_rate=48000, put_accent=True, put_yo=True)
    arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
    sd.play(arr, 48000)
    sd.wait()
    print("  OK")

print("\nВсе голоса (y/n)?", end=" ", flush=True)
if input().strip().lower() == "y":
    for spk in ["aidar", "baya", "kseniya", "xenia", "eugene"]:
        print(f"  {spk}...", end=" ", flush=True)
        with torch.no_grad():
            audio = model.apply_tts(text=f"Меня зовут {spk}, сэр.",
                                    speaker=spk, sample_rate=48000)
        arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
        sd.play(arr, 48000); sd.wait()
        print("ok")
    print("\nУкажи голос в config.yaml -> silero_speaker: 'aidar'")

print("\n=== ГОЛОС РАБОТАЕТ! Запускай: python main.py ===")
