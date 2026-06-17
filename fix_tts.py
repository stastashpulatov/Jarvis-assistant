"""
Полный ремонт chatterbox/tts.py:
1. Показывает строки вокруг проблемного места
2. Восстанавливает оригинал если сломан
3. Применяет чистый патч
"""
import os, sys, importlib.util

spec     = importlib.util.find_spec("chatterbox")
tts_file = os.path.join(os.path.dirname(spec.origin), "tts.py")
print(f"File: {tts_file}\n")

with open(tts_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Показываем строки 120-140 для диагностики
print("=== Lines 120-145 ===")
for i, l in enumerate(lines[119:144], start=120):
    print(f"{i:4d}: {repr(l)}")
print()

# Проверяем что сломано
broken1 = any("try:" in l and i > 0 and "watermarker" not in lines[i-1]
               and "watermarker" not in lines[i+1] if i+1 < len(lines) else False
               for i, l in enumerate(lines))

# Ищем все строки с watermark
watermark_lines = [(i+1, l.rstrip()) for i, l in enumerate(lines) if "watermark" in l.lower()]
print("=== All watermark lines ===")
for ln, l in watermark_lines:
    print(f"  {ln}: {repr(l)}")
print()

# Стратегия: найти блок try: ... и починить его
new_lines = []
i = 0
patched = []

while i < len(lines):
    line = lines[i]

    # Ищем сломанный паттерн: "try:\n" за которым сразу "try:\n" или пустая строка
    # ИЛИ оригинальный: "self.watermarker = perth.PerthImplicitWatermarker()"
    # ИЛИ уже частично пропатченный мусор

    stripped = line.strip()

    # Случай 1: старый сломанный патч — "try:" без тела, за ним сразу ещё "try:"
    if stripped == "try:" and i + 1 < len(lines) and lines[i+1].strip() == "try:":
        # Пропускаем лишний try:
        print(f"Skipping broken try: at line {i+1}")
        i += 1
        continue

    # Случай 2: "self.watermarker = perth..." — оригинал или уже в try блоке
    if "self.watermarker = perth.PerthImplicitWatermarker()" in line:
        indent = len(line) - len(line.lstrip())
        sp = " " * indent

        # Проверяем предыдущую строку — уже есть try?
        prev = lines[i-1].strip() if i > 0 else ""
        if prev == "try:":
            # Уже начали патч, добавляем except
            new_lines.append(line)  # сама строка
            new_lines.append(sp + "except Exception:\n")
            new_lines.append(sp + "    self.watermarker = None\n")
            patched.append(f"Patch 1 completed at line {i+1}")
        else:
            # Оригинальный — оборачиваем
            new_lines.append(sp + "try:\n")
            new_lines.append(sp + "    self.watermarker = perth.PerthImplicitWatermarker()\n")
            new_lines.append(sp + "except Exception:\n")
            new_lines.append(sp + "    self.watermarker = None\n")
            patched.append(f"Patch 1 fresh at line {i+1}")
        i += 1
        continue

    # Случай 3: apply_watermark — оригинальный
    if "watermarked_wav = self.watermarker.apply_watermark(" in line and "if self.watermarker" not in (lines[i-1] if i > 0 else ""):
        indent = len(line) - len(line.lstrip())
        sp = " " * indent
        new_lines.append(sp + "if self.watermarker is not None:\n")
        new_lines.append(sp + "    watermarked_wav = self.watermarker.apply_watermark(wav, sample_rate=self.sr)\n")
        new_lines.append(sp + "else:\n")
        new_lines.append(sp + "    watermarked_wav = wav\n")
        patched.append(f"Patch 2 at line {i+1}")
        i += 1
        continue

    new_lines.append(line)
    i += 1

print("Patches applied:", patched)

with open(tts_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\nFile written. Verifying syntax...")
import subprocess
result = subprocess.run(
    [sys.executable, "-c", f"import py_compile; py_compile.compile(r'{tts_file}', doraise=True)"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("Syntax OK! Run: python test_voice.py")
else:
    print(f"Syntax ERROR: {result.stderr}")
    print("\nLines around problem:")
    for i, l in enumerate(new_lines[120:145], start=121):
        print(f"  {i}: {repr(l)}")
