"""Загрузчик конфигурации из config.yaml"""
import copy
import os
import yaml

_DEFAULT_CONFIG = {
    "A": {
        "name": "J.A.R.V.I.S.",
        "wakeword": "джарвис",
        "command_timeout": 12,
        "idle_timeout": 90,
        "always_on": True,
    },
    "audio": {
        "silence_timeout": 1.0,
        "energy_threshold": 300,
        "phrase_limit": 10,
    },
    "voice": {
        "engine": "silero",
        "silero_speaker": "aidar",
        "offline_rate": 160,
        "offline_volume": 1.0,
        "rvc_pitch_shift": 0,
    },
    "gemini": {
        "api_key": "",
        "model": "gemini-2.5-flash",
        "max_tokens": 600,
        "temperature": 0.7,
        "quota_cooldown_seconds": 90,
    },
    "ai": {
        "provider": "ollama",
        "fallback_provider": "gemini",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434",
        "model": "qwen2.5:7b-instruct",
        "fallback_model": "qwen2.5:3b-instruct",
        "num_predict": 160,
        "temperature": 0.35,
        "timeout": 45,
    },
    "logging": {
        "enabled": True,
        "level": "INFO",
    },
    "jarvis": {
        "user_name": "сэр",
        "city": "Tashkent",
        "boot_animation": True,
        "proactive": False,
        "suggestion_interval": 1200,
        "focus_minutes": 50,
        "break_minutes": 10,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(path: str = "config.yaml") -> dict:
    cfg = copy.deepcopy(_DEFAULT_CONFIG)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, user)
        except Exception as e:
            print(f"[КОНФИГ] Ошибка чтения config.yaml: {e}. Использую настройки по умолчанию.")
    else:
        print("[КОНФИГ] config.yaml не найден, использую настройки по умолчанию.")
    return cfg
