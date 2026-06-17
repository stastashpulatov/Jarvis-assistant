"""
Находит правильный ключ для загрузки модели из v4_ru.pt
python find_key.py
"""
import torch, pathlib, sys

hub_dir = pathlib.Path(torch.hub.get_dir())
pt_path = None
for d in hub_dir.glob("snakers4_silero*"):
    p = d / "src" / "silero" / "model" / "v4_ru.pt"
    if p.exists():
        pt_path = p
        break

print(f"Файл: {pt_path}\n")

imp = torch.package.PackageImporter(str(pt_path))

# Смотрим все файлы внутри архива
print("=== Все файлы в архиве ===")
def walk(node, prefix=""):
    for name, child in node.children.items():
        full = f"{prefix}/{name}" if prefix else name
        if hasattr(child, 'children') and child.children:
            walk(child, full)
        else:
            print(f"  {full}")

walk(imp.file_structure())

# Ищем все pickle файлы
print("\n=== Ищу pickle файлы ===")
import zipfile
with zipfile.ZipFile(str(pt_path)) as z:
    for name in z.namelist():
        if not name.startswith(".data"):
            print(f"  {name}")

# Пробуем загрузить каждый pickle
print("\n=== Пробую все пикл-файлы ===")
with zipfile.ZipFile(str(pt_path)) as z:
    pickles = [n for n in z.namelist()
               if not n.startswith(".data") and "/" in n]
    for pkl_path in pickles:
        parts = pkl_path.split("/")
        if len(parts) == 2:
            module, name = parts[0], parts[1]
            try:
                obj = imp.load_pickle(module, name)
                print(f"  load_pickle('{module}', '{name}') -> {type(obj).__name__}")
                if obj is not None and hasattr(obj, 'apply_tts'):
                    print(f"  *** НАШЁЛ! apply_tts=True ***")
                    print(f"  Используй: imp.load_pickle('{module}', '{name}')")
            except Exception as e:
                print(f"  load_pickle('{module}', '{name}') -> ОШИБКА: {str(e)[:50]}")
