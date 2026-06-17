#!/usr/bin/env python
"""Test TTS Engine initialization logic"""

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

print(f"Config engine: {config['voice']['engine']}")
print()

# Test TTSEngine init
from core.tts import TTSEngine

logger = MockLog()
engine = TTSEngine(config, logger)

print()
print(f"Final mode: {engine._mode}")
print(f"Sample mode: {engine._sample_mode}")
print(f"Voice samples: {engine._voice_samples}")
