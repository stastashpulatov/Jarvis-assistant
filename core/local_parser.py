"""
Быстрый локальный парсер команд — без обращения к Gemini.
Обрабатывает типичные фразы за миллисекунды.
"""
import re
from rapidfuzz import fuzz, process
from . import actions as A
from .protocols import match_protocol


URL_HINTS: dict[str, str] = {
    "youtube":       "https://www.youtube.com",
    "ютуб":          "https://www.youtube.com",
    "ютюб":          "https://www.youtube.com",
    "google":        "https://www.google.com",
    "гугл":          "https://www.google.com",
    "github":        "https://github.com",
    "гитхаб":        "https://github.com",
    "python docs":   "https://docs.python.org/3/",
    "python":        "https://docs.python.org/3/",
    "питон":         "https://docs.python.org/3/",
    "документация питона": "https://docs.python.org/3/",
    "документацию питона": "https://docs.python.org/3/",
    "документация python": "https://docs.python.org/3/",
    "stackoverflow": "https://stackoverflow.com",
    "reddit":        "https://www.reddit.com",
    "vk":            "https://vk.com",
    "вконтакте":     "https://vk.com",
    "telegram web":  "https://web.telegram.org",
    "chatgpt":       "https://chatgpt.com",
    "чатгпт":        "https://chatgpt.com",
    "яндекс":        "https://ya.ru",
    "mail":          "https://mail.ru",
    "почта":         "https://mail.ru",
    "gmail":         "https://mail.google.com",
    "карты":         "https://www.google.com/maps",
    "google maps":   "https://www.google.com/maps",
    "переводчик":    "https://translate.google.com",
    "translate":     "https://translate.google.com",
}

BROWSER_WORDS = {
    "edge", "msedge", "microsoft edge", "эдж", "майкрософт эдж", "майкрософт edge",
    "chrome", "хром", "гугл хром", "google chrome",
    "firefox", "файрфокс",
}

VOLUME_WORDS = ("звук", "громк", "volume", "sound", "audio")

APP_OPEN_RE = re.compile(
    r"^(?:открой|запусти|включи|активируй|вруби|покажи|launch|open|start)\s+"
    r"(?:(?:мне|пожалуйста)\s+)?(?:программу\s+|приложение\s+|app\s+)?(.+)$",
    re.IGNORECASE,
)

SEARCH_RE = re.compile(
    r"^(?:найди|найти|поиск|search|загугли|гугл)\s+(.+)$",
    re.IGNORECASE,
)

CLOSE_RE = re.compile(
    r"^(?:закрой|закрыть|close|kill)\s+(.+)$",
    re.IGNORECASE,
)

NOTE_RE = re.compile(
    r"^(?:запиши|запомни|создай заметку|заметка|note)\s*(?:заметку\s*)?(?:что\s*)?(.+)$",
    re.IGNORECASE,
)

FOLDER_RE = re.compile(
    r"^(?:открой|покажи|open)\s+(?:папку\s+)?"
    r"(загрузки|downloads|документы|documents|рабочий стол|desktop|изображения|pictures|музыка|music|видео|videos)$",
    re.IGNORECASE,
)

TIMER_RE = re.compile(
    r"(?:таймер|напомни|remind|timer).*?(?:на|через|for)\s+(\d{1,3})\s*"
    r"(секунд\w*|сек|seconds?|минут\w*|мин|minutes?|час\w*|hours?)"
    r"(?:\s+(?:что|о том что|про|about)\s+(.+))?",
    re.IGNORECASE,
)

WEATHER_RE = re.compile(
    r"(?:погод\w*|weather).*?(?:в|in|for)\s+(.+?)(?:\?|$)",
    re.IGNORECASE,
)
WEATHER_SIMPLE_RE = re.compile(
    r"^(?:какая погода|погода|weather)(?:\s+(?:в|in|for)\s+(.+))?$",
    re.IGNORECASE,
)

# Установка громкости на N — проверяется ДО up/down
VOLUME_SET_PATTERNS = [
    re.compile(r"(?:постав|установ|выстав|сделай|set)\w*\s+(?:звук|громкост\w*|volume)\s*(?:на|до|at)?\s*(\d{1,3})\s*(?:%|процент\w*)?", re.I),
    re.compile(r"(?:звук|громкост\w*|volume)\s*(?:на|до|at)\s*(\d{1,3})\s*(?:%|процент\w*)?", re.I),
    re.compile(r"(?:уменьш|увелич|пони|подн|lower|raise|increase|decrease)\w*\s+(?:звук|громкост\w*|volume)\s*(?:до|на|to|at)\s*(\d{1,3})\s*(?:%|процент\w*)?", re.I),
    re.compile(r"^(?:звук|громкост\w*|volume)\s*(\d{1,3})\s*(?:%|процент\w*)?$", re.I),
    re.compile(r"^(\d{1,3})\s*(?:%|процент\w*)$", re.I),
]

APP_ALIAS_LIST = list(A.APP_ALIASES.keys())


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _resolve_app(name: str) -> str:
    key = name.strip().lower()
    if key in A.APP_ALIASES:
        return A.APP_ALIASES[key]
    match = process.extractOne(key, APP_ALIAS_LIST, scorer=fuzz.WRatio, score_cutoff=75)
    if match:
        return A.APP_ALIASES[match[0]]
    return key


def _resolve_browser(text: str) -> str | None:
    t = _normalize(text)
    for word in sorted(BROWSER_WORDS, key=len, reverse=True):
        if word in t:
            return A.APP_ALIASES.get(word, word)
    return None


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for m in re.finditer(r"https?://[^\s,]+", text, re.IGNORECASE):
        url = m.group(0).rstrip(".,)")
        if url not in seen:
            urls.append(url)
            seen.add(url)

    t = _normalize(text)
    for hint, url in sorted(URL_HINTS.items(), key=lambda x: len(x[0]), reverse=True):
        if hint in t and url not in seen:
            urls.append(url)
            seen.add(url)

    return urls


def _is_volume_context(text: str) -> bool:
    t = _normalize(text)
    return any(w in t for w in VOLUME_WORDS)


def _match_volume_set(text: str, ctx: dict | None = None) -> int | None:
    raw = text.strip()
    t = _normalize(raw)

    for i, pattern in enumerate(VOLUME_SET_PATTERNS):
        m = pattern.search(raw if i < 4 else t)
        if m:
            level = int(m.group(1))
            if 0 <= level <= 100:
                return level

    # Короткий ответ «60» после разговора о громкости
    if ctx and ctx.get("awaiting_volume"):
        m = re.match(r"^(\d{1,3})\s*(?:%|процент\w*)?\.?$", raw, re.I)
        if m:
            level = int(m.group(1))
            if 0 <= level <= 100:
                return level

    return None


def _match_app_open(text: str) -> tuple[str, str] | None:
    m = APP_OPEN_RE.match(text.strip())
    if not m:
        return None
    target = m.group(1).strip()
    if _extract_urls(target) or "вкладк" in target or "tab" in target:
        return None
    target = re.sub(r"^(?:мне|пожалуйста)\s+", "", target, flags=re.I)
    target = re.sub(r"\s*(?:сэр|please|пожалуйста)\.?\s*$", "", target, flags=re.I)
    if not target:
        return None
    return _resolve_app(target), target


def _match_timer(text: str) -> tuple[int, str] | None:
    m = TIMER_RE.search(text)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2).lower()
    message = (m.group(3) or "таймер завершён").strip().rstrip(".")
    if unit.startswith(("сек", "sec")):
        seconds = value
    elif unit.startswith(("час", "hour")):
        seconds = value * 3600
    else:
        seconds = value * 60
    return seconds, message


def try_parse(text: str, ctx: dict | None = None) -> tuple[str, list[dict]] | None:
    """
    Пытается распознать команду локально.
    ctx — контекст: awaiting_volume, awaiting_confirm, default_city
    """
    raw = text.strip()
    if not raw:
        return None

    t = _normalize(raw)
    ctx = ctx or {}

    # ── Подтверждение опасных команд ──────────────────────────────
    if ctx.get("awaiting_confirm"):
        if re.search(r"\b(да|подтвержда|confirm|yes|выполня|соглас)\b", t):
            action = ctx.pop("pending_action", None)
            ctx["awaiting_confirm"] = False
            if action:
                return "Выполняю, сэр.", [action]
        if re.search(r"\b(нет|отмен|cancel|no|стоп)\b", t):
            ctx["awaiting_confirm"] = False
            ctx.pop("pending_action", None)
            return "Отменено, сэр.", [{"action": "none"}]
        return "Сэр, скажите «да» для подтверждения или «нет» для отмены.", [{"action": "none"}]

    # ── Протоколы (режимы из фильма) ──────────────────────────────
    proto = match_protocol(raw)
    if proto:
        return proto

    # ── Кто ты / JARVIS ───────────────────────────────────────────
    if re.search(r"\b(кто ты|что ты|who are you|представься|ты jarvis|ты джарвис)\b", t):
        from .personality import identity_line
        return identity_line(), [{"action": "none"}]

    # ── Быстрая помощь и предложения ─────────────────────────────
    if re.search(r"\b(что умеешь|что ты умеешь|помощь|help|команды|что можешь)\b", t):
        from .personality import quick_help_line
        return quick_help_line(), [{"action": "none"}]

    if re.search(r"\b(что предложишь|предложи|совет|идея|чем займемся|чем займёмся)\b", t):
        from .personality import proactive_line
        return proactive_line(), [{"action": "none"}]

    if re.search(r"\b(перерыв|отдохнуть|устал|устала|break)\b", t):
        return (
            "Сэр, предлагаю десять минут перерыва: вода, разминка плеч и отдых для глаз. "
            "Когда вернётесь, скажите «рабочий режим».",
            [{"action": "none"}],
        )

    # ── Заметки и таймеры ────────────────────────────────────────
    m = NOTE_RE.match(raw)
    if m:
        return "", [{"action": "create_note", "text": m.group(1).strip()}]

    timer = _match_timer(raw)
    if timer:
        seconds, message = timer
        return "", [{"action": "timer", "seconds": seconds, "message": message}]

    # ── Погода ────────────────────────────────────────────────────
    m = WEATHER_RE.search(raw)
    if m:
        city = m.group(1).strip().rstrip(".")
        return "", [{"action": "weather", "city": city}]
    m = WEATHER_SIMPLE_RE.match(raw)
    if m:
        city = (m.group(1) or ctx.get("default_city", "Moscow")).strip()
        return "", [{"action": "weather", "city": city}]

    # ── Диагностика ───────────────────────────────────────────────
    if re.search(r"\b(диагностик\w*|diagnostic\w*|сканирован\w*|проверь (?:все )?систем\w*)\b", t):
        return "Запускаю диагностику, сэр.", [{"action": "diagnostics"}]

    # ── Батарея ───────────────────────────────────────────────────
    if re.search(r"\b(батаре|заряд|battery|аккумулятор)\b", t):
        return "", [{"action": "battery"}]

    # ── Рабочий стол ──────────────────────────────────────────────
    if re.search(r"\b(покажи рабочий стол|сверни (?:все )?окн|show desktop|минимизируй)\b", t):
        return "", [{"action": "show_desktop"}]

    m = FOLDER_RE.match(raw)
    if m:
        return "", [{"action": "open_folder", "target": m.group(1).strip()}]

    # ── Очистить корзину ──────────────────────────────────────────
    if re.search(r"\b(очисти корзин|empty trash|пуст.*корзин)\b", t):
        return "Очищаю корзину, сэр.", [{"action": "empty_trash"}]

    # ── Громкость на N% (ПЕРВЫМ — до up/down) ────────────────────
    level = _match_volume_set(raw, ctx)
    if level is not None:
        ctx["awaiting_volume"] = False
        return "", [{"action": "volume_set", "level": level}]

    # ── Текущая громкость ─────────────────────────────────────────
    if re.search(r"\b(какая громкость|какой звук|сколько громк|уровень звук|volume level|how loud)\b", t):
        return "", [{"action": "volume_get"}]

    # ── Громкость up/down/mute ────────────────────────────────────
    if re.search(r"\b(громче|погромче|volume up|увелич.*громк)\b", t) and not re.search(r"\d", t):
        return "", [{"action": "volume_up"}]
    if re.search(r"\b(тише|потише|volume down)\b", t) and not re.search(r"\d", t):
        return "", [{"action": "volume_down"}]
    if re.search(r"\b(без звука|заглуш|mute|выключ.*звук)\b", t):
        return "", [{"action": "volume_mute"}]

    # ── Медиа ────────────────────────────────────────────────────
    if re.search(r"\b(пауза|play pause|play|pause|продолжи|останови музыку|поставь на паузу)\b", t):
        return "", [{"action": "media_play_pause"}]
    if re.search(r"\b(следующий трек|следующая песня|next track|next song|дальше)\b", t):
        return "", [{"action": "media_next"}]
    if re.search(r"\b(предыдущий трек|предыдущая песня|previous track|prev song|назад трек)\b", t):
        return "", [{"action": "media_previous"}]

    # Запоминаем контекст для follow-up «60»
    if _is_volume_context(t) and re.search(r"\b(на|до|установ|постав)\b", t):
        ctx["awaiting_volume"] = True

    # ── Браузер + сайты ───────────────────────────────────────────
    urls = _extract_urls(raw)
    browser = _resolve_browser(raw)
    if urls and (browser or "браузер" in t or "browser" in t or len(urls) >= 2):
        browser = browser or "msedge"
        if len(urls) == 1:
            speech = f"Открываю сайт в браузере, сэр."
        else:
            speech = f"Открываю {len(urls)} вкладки в браузере, сэр."
        return speech, [{"action": "open_urls", "browser": browser, "urls": urls}]

    if urls and any(w in t for w in ("открой", "open", "перейди", "go to", "зайди")):
        if len(urls) == 1:
            return "Открываю сайт, сэр.", [{"action": "open_url", "target": urls[0], "browser": browser}]
        return f"Открываю {len(urls)} вкладки, сэр.", [{"action": "open_urls", "browser": browser or "msedge", "urls": urls}]

    # ── Время / система ───────────────────────────────────────────
    if re.search(r"\b(который час|какое время|сколько времени|what time)\b", t):
        return "", [{"action": "show_time"}]
    if re.search(r"\b(система|system info|нагрузка|cpu|память)\b", t) and "открой" not in t:
        return "", [{"action": "system_info"}]
    if re.search(r"\b(скриншот|screenshot|снимок экрана)\b", t):
        return "", [{"action": "screenshot"}]

    # ── Питание (с подтверждением) ────────────────────────────────
    if re.search(r"\b(выключ\w*\s.*комп|shutdown|выключ.*пк)\b", t):
        ctx["awaiting_confirm"] = True
        ctx["pending_action"] = {"action": "shutdown"}
        return "Сэр, вы уверены? Подтвердите выключение.", [{"action": "none"}]
    if re.search(r"\b(перезагруз|restart|reboot)\b", t):
        ctx["awaiting_confirm"] = True
        ctx["pending_action"] = {"action": "restart"}
        return "Сэр, подтвердите перезагрузку системы.", [{"action": "none"}]
    if re.search(r"\b(заблокиру|lock|блокиров.*экран)\b", t):
        return "Блокирую компьютер, сэр.", [{"action": "lock"}]

    # ── Поиск ─────────────────────────────────────────────────────
    m = SEARCH_RE.match(raw)
    if m:
        q = m.group(1).strip()
        return f"Ищу «{q}», сэр.", [{"action": "search_web", "query": q}]

    # ── Закрыть приложение ────────────────────────────────────────
    m = CLOSE_RE.match(raw)
    if m:
        target = _resolve_app(m.group(1).strip())
        return f"Закрываю {target}, сэр.", [{"action": "close_app", "target": target}]

    # ── Открыть приложение ────────────────────────────────────────
    app_match = _match_app_open(raw)
    if app_match:
        internal, spoken = app_match
        label = spoken if spoken != internal else internal
        return f"Запускаю {label}, сэр.", [{"action": "open_app", "target": internal}]

    return None
