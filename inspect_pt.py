"""
Инспектирует v4_ru.pt и находит правильные ключи для загрузки модели.
python inspect_pt.py
"""
import pathlib, sys

# Ищем v4_ru.pt
import torch
hub_dir = pathlib.Path(torch.hub.get_dir())
pt_path = None
for d in hub_dir.glob("snakers4_silero*"):
    for pt in d.rglob("v4_ru.pt"):
        pt_path = pt
        break

if not pt_path:
    print("v4_ru.pt не найден!")
    sys.exit(1)

print(f"Файл: {pt_path} ({pt_path.stat().st_size // 1024}KB)\n")

# Смотрим содержимое через PackageImporter
print("=== Содержимое .pt архива ===")
try:
    imp = torch.package.PackageImporter(str(pt_path))
    # Список всех файлов внутри
    for name in imp.file_structure().children:
        print(f"  ROOT/{name}")
        try:
            node = imp.file_structure().children[name]
            for child in node.children:
                print(f"    {name}/{child}")
        except Exception:
            pass
except Exception as e:
    print(f"PackageImporter ошибка: {e}")

# Пробуем разные ключи
print("\n=== Пробую разные ключи загрузки ===")
keys_to_try = [
    ("tts_models", "model"),
    ("tts_models", "tts_model"),
    ("model", "model"),
    ("models", "model"),
    ("silero_tts", "model"),
]
for module, attr in keys_to_try:
    try:
        imp = torch.package.PackageImporter(str(pt_path))
        obj = imp.load_pickle(module, attr)
        print(f"  load_pickle('{module}', '{attr}') → {type(obj)}")
        if obj is not None:
            print(f"    *** РАБОТАЕТ! has apply_tts={hasattr(obj, 'apply_tts')} ***")
    except Exception as e:
        print(f"  load_pickle('{module}', '{attr}') → ОШИБКА: {str(e)[:60]}")

# Пробуем torch.load напрямую
print("\n=== torch.load напрямую ===")
try:
    obj = torch.load(str(pt_path), map_location="cpu", weights_only=False)
    print(f"torch.load → {type(obj)}")
    if isinstance(obj, dict):
        print(f"  ключи: {list(obj.keys())[:10]}")
    elif obj is not None:
        print(f"  has apply_tts: {hasattr(obj, 'apply_tts')}")
        if hasattr(obj, 'apply_tts'):
            print("  *** РАБОТАЕТ через torch.load! ***")
except Exception as e:
    print(f"torch.load ошибка: {e}")
