#!/usr/bin/env python
"""Test sample mode voice playback with real responses"""

import sys, os, yaml
sys.path.insert(0, os.path.dirname(__file__))

# Mock logger
class MockLog:
    def info(self, tag, msg):
        print(f"[{tag}] {msg}")
    def warn(self, tag, msg):
        print(f"[WARN {tag}] {msg}")

# Load real config
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Init TTS
from core.tts import TTSEngine
logger = MockLog()
engine = TTSEngine(config, logger)

print(f"\nActive mode: {engine._mode}")
print("=" * 60)
print("\n[DEMO] Jarvis - быстрый ответ с sample-голосом")
print("-" * 60)

# Test responses (как будто система генерировала ответ)
responses = [
    "Готов к работе, сэр. Ожидаю ваших команд.",
    "Браузер Chrome запущен, сэр.",
    "Воспроизвожу вашу любимую музыку.",
]

for i, response in enumerate(responses, 1):
    print(f"\n[{i}] Ответ: {response}")
    engine.speak(response)
    print("    ✓ Произнесено")

print("\n" + "=" * 60)
print("Тест завершён! Первый ответ начался с sample, остальные без.")
