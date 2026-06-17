"""
Протоколы JARVIS — сценарии из «Железного человека».
Каждый протокол = реплика + список действий.
"""
import re

# name -> (speech, actions, aliases)
PROTOCOLS: dict[str, tuple] = {
    "work": (
        "Активирую рабочий протокол, сэр. Подготавливаю рабочее окружение.",
        [
            {"action": "open_app", "target": "vscode"},
            {"action": "open_urls", "browser": "msedge",
             "urls": ["https://github.com", "https://stackoverflow.com"]},
            {"action": "volume_set", "level": 40},
        ],
        ("рабоч", "work", "работ", "код", "программ"),
    ),
    "gaming": (
        "Игровой протокол активирован, сэр. Приятной игры.",
        [
            {"action": "open_app", "target": "steam"},
            {"action": "open_app", "target": "discord"},
            {"action": "volume_set", "level": 75},
        ],
        ("игр", "gaming", "game", "стим", "steam"),
    ),
    "presentation": (
        "Режим презентации, сэр. Отключаю отвлекающие элементы.",
        [
            {"action": "show_desktop"},
            {"action": "volume_set", "level": 50},
        ],
        ("презентац", "presentation", "доклад", "выступлен"),
    ),
    "night": (
        "Ночной протокол, сэр. Снижаю уровень шума.",
        [
            {"action": "volume_set", "level": 15},
        ],
        ("ночн", "night", "спать", "sleep", "тих"),
    ),
    "lockdown": (
        "Экстренный протокол. Блокирую систему, сэр.",
        [
            {"action": "lock"},
        ],
        ("экстрен", "lockdown", "тревог", "блокиров", "emergency", "протокол безопас"),
    ),
    "diagnostics": (
        "Запускаю полную диагностику всех систем, сэр.",
        [{"action": "diagnostics"}],
        ("диагност", "diagnostic", "сканирован", "проверь систем", "полная проверк"),
    ),
    "cinema": (
        "Кинорежим, сэр. Наслаждайтесь просмотром.",
        [
            {"action": "open_app", "target": "vlc"},
            {"action": "volume_set", "level": 60},
            {"action": "show_desktop"},
        ],
        ("кино", "cinema", "фильм", "movie", "видео"),
    ),
    "focus": (
        "Режим концентрации, сэр. Минимум отвлечений.",
        [
            {"action": "close_app", "target": "discord"},
            {"action": "close_app", "target": "telegram"},
            {"action": "volume_set", "level": 25},
        ],
        ("фокус", "focus", "концентрац", "не отвлек"),
    ),
}


def match_protocol(text: str) -> tuple[str, list[dict]] | None:
    t = text.lower()
    if not re.search(r"\b(протокол|режим|protocol|mode|активиру|включ)\b", t):
        # диагностика без слова «протокол»
        if re.search(r"\b(полная диагностика|диагностика систем|scan system)\b", t):
            p = PROTOCOLS["diagnostics"]
            return p[0], list(p[1])
        return None

    for key, (speech, actions, aliases) in PROTOCOLS.items():
        if any(a in t for a in aliases):
            return speech, list(actions)
    return None
