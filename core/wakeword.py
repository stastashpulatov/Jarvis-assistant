"""
Детектор кодового слова.
Использует rapidfuzz для нечёткого совпадения — ловит «жарвис», «харвис» и т.д.
"""

_RF_AVAILABLE = False
try:
    from rapidfuzz import fuzz
    _RF_AVAILABLE = True
except ImportError:
    pass

# Все варианты произношения
_WAKE_VARIANTS = [
    "джарвис", "jarvis", "жарвис", "дарвис",
    "харвис", "джарвіс", "жарвіс", "жарвус",
]

# Команды деактивации
_DEACTIVATE = {
    "отбой", "отдохни", "отдыхай", "свободен",
    "стоп", "молчи", "хватит", "пока", "до свидания",
    "standby",
}


def is_wake(text: str, wakeword: str, threshold: int = 72) -> bool:
    """Возвращает True если в тексте есть кодовое слово (с нечётким совпадением)"""
    t = text.lower()
    variants = _WAKE_VARIANTS + [wakeword.lower()]

    for v in variants:
        if v in t:
            return True

    if _RF_AVAILABLE:
        words = t.split()
        for word in words:
            for v in variants:
                score = fuzz.ratio(word, v)
                if score >= threshold:
                    return True
    return False


def is_deactivate(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in _DEACTIVATE)


def strip_wake(text: str, wakeword: str) -> str:
    """Убирает кодовое слово из фразы"""
    import re
    t = text.lower()
    variants = _WAKE_VARIANTS + [wakeword.lower()]
    for v in sorted(variants, key=len, reverse=True):
        t = t.replace(v, "")
    t = re.sub(r'^[\s,\-–—\.]+', '', t)
    return t.strip()
