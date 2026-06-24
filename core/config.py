"""Загрузчик конфигурации из config.yaml"""
import copy
import os
import yaml
from dotenv import load_dotenv
load_dotenv()

_DEFAULT_CONFIG = {
    "A": {
        "name": "J.A.R.V.I.S.",
        "wakeword": "джарвис",
        "command_timeout": 8,  # Уменьшено для скорости
        "idle_timeout": 60,
        "always_on": True,
    },
    "audio": {
        "silence_timeout": 0.4,  # Ещё меньше для скорости
        "energy_threshold": 300,
        "phrase_limit": 2,  # Ещё меньше для скорости
    },
    "voice": {
        "engine": "silero",
        "silero_speaker": "aidar",
        "offline_rate": 200,  # Ещё быстрее речь
        "offline_volume": 1.0,
        "rvc_pitch_shift": 0,
        "enable_rvc": False,  # Отключено для скорости
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
        "model": "qwen2.5:3b-instruct",  # 3b модель как основная для стабильности
        "fallback_model": "qwen2.5:3b-instruct",
        "num_predict": 60,
        "temperature": 0.7,
        "timeout": 15,
        "stream": False,
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
        "preload_ai": False,  # Отключено из-за ошибок Ollama
        "suggestion_interval": 1200,
        "focus_minutes": 50,
        "break_minutes": 10,
        "cache_enabled": True,
        "performance_monitoring": False,
        "enable_tray": True,  # Системный трей
        "enable_telegram": False,  # Telegram-бот
        "telegram_token": "",  # Токен бота
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
    
    if os.getenv("GEMINI_API_KEY"):
        cfg["gemini"]["api_key"] = os.getenv("GEMINI_API_KEY")
    
    return cfg
