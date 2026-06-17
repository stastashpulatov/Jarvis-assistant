"""
Извлекает модель Silero из вложенного архива и тестирует голос.
python fix_silero.py
"""
import torch, pathlib, zipfile, sys, struct

hub_dir = pathlib.Path(torch.hub.get_dir())
pt_path = None
for d in hub_dir.glob("snakers4_silero*"):
    p = d / "src" / "silero" / "model" / "v4_ru.pt"
    if p.exists():
        pt_path = p
        break

if not pt_path:
    print("v4_ru.pt не найден!")
    sys.exit(1)

print(f"Исходный файл: {pt_path}\n")

# Смотрим что внутри
with zipfile.ZipFile(str(pt_path)) as z:
    names = z.namelist()

# Определяем префикс
prefixes = set()
for n in names:
    if "/" in n:
        prefixes.add(n.split("/")[0])
print(f"Префиксы в архиве: {prefixes}")

# Находим основной префикс (не .data)
main_prefix = None
for p in prefixes:
    if not p.startswith("."):
        main_prefix = p
        break

print(f"Основной префикс: {main_prefix!r}")
print(f"Всего файлов: {len(names)}\n")

# Извлекаем правильно - создаём новый zip
extracted = pt_path.parent / "v4_ru_fixed.pt"

print("Создаю исправленный архив...")
with zipfile.ZipFile(str(pt_path), "r") as src:
    with zipfile.ZipFile(str(extracted), "w", compression=zipfile.ZIP_STORED) as dst:
        for item in src.infolist():
            name = item.filename
            
            if main_prefix and name.startswith(main_prefix + "/"):
                # Убираем prefix "v4_ru/" → оставляем остаток
                new_name = name[len(main_prefix) + 1:]
            else:
                new_name = name
            
            if not new_name:  # пропускаем корневую папку
                continue
                
            data = src.read(item.filename)
            info = zipfile.ZipInfo(new_name)
            info.compress_type = zipfile.ZIP_STORED
            dst.writestr(info, data)

sz = extracted.stat().st_size // 1024
print(f"Создан: {extracted} ({sz}KB)\n")

# Проверяем что внутри нового архива
with zipfile.ZipFile(str(extracted)) as z:
    new_names = z.namelist()
    print("Ключевые файлы в новом архиве:")
    for n in new_names:
        if "extern" in n or "tts_models" in n or "python_version" in n or "version" in n:
            print(f"  {n}")

print("\nЗагружаю модель...")
try:
    imp = torch.package.PackageImporter(str(extracted))
    model = imp.load_pickle("tts_models", "model")
    
    if model is None:
        print("model = None, пробую другие ключи...")
        with zipfile.ZipFile(str(extracted)) as z:
            for n in z.namelist():
                if "/" in n and not n.startswith(".") and not n.endswith("/"):
                    parts = n.split("/")
                    if len(parts) == 2:
                        try:
                            obj = imp.load_pickle(parts[0], parts[1])
                            print(f"  {parts[0]}/{parts[1]} -> {type(obj).__name__}")
                        except Exception as e:
                            pass
    else:
        print(f"Модель: {type(model).__name__}")
        print(f"apply_tts: {hasattr(model, 'apply_tts')}")
        
        if hasattr(model, 'apply_tts'):
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            
            import sounddevice as sd
            print(f"\nГенерирую тест на {device}...")
            with torch.no_grad():
                audio = model.apply_tts(
                    text="Все системы онлайн, сэр. Джарвис готов.",
                    speaker="aidar",
                    sample_rate=48000,
                    put_accent=True,
                    put_yo=True,
                )
            arr = audio.numpy()
            sd.play(arr, 48000)
            sd.wait()
            print("✓ ГОЛОС РАБОТАЕТ!")
            
            # Патчим core/tts.py — добавляем путь к исправленному файлу
            tts_path = pathlib.Path("core/tts.py")
            content = tts_path.read_text(encoding="utf-8")
            fixed_str = str(extracted).replace("\\", "/")
            
            new_method = f'''    def _find_silero_pt(self) -> pathlib.Path | None:
        fixed = pathlib.Path(r"{str(extracted)}")
        if fixed.exists():
            return fixed
        import torch as _t
        h = pathlib.Path(_t.hub.get_dir())
        for d in h.glob("snakers4_silero*"):
            for pt in d.rglob("v4_ru_fixed.pt"):
                return pt
            for pt in d.rglob("v4_ru.pt"):
                return pt
        return None
'''
            import re
            new_content = re.sub(
                r'    def _find_silero_pt\(self\).*?(?=\n    def |\nclass )',
                new_method,
                content,
                flags=re.DOTALL
            )
            tts_path.write_text(new_content, encoding="utf-8")
            print("\ncore/tts.py обновлён ✓")
            print("Запускай: python main.py")

except Exception as e:
    import traceback
    traceback.print_exc()
