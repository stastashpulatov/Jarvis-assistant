"""
Быстрый локальный парсер команд — без обращения к Gemini.
Обрабатывает типичные фразы за миллисекунды.
"""
import re
from rapidfuzz import fuzz, process
from functools import lru_cache
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

# Паттерны, которые раньше компилировались внутри try_parse при каждом вызове
_LIST_FILES_RE     = re.compile(r"\b(список файлов|list files)\s+(.+)$", re.I)
_DELETE_FILE_RE    = re.compile(r"\b(удали файл|delete file)\s+(.+)$", re.I)
_CREATE_FOLDER_RE  = re.compile(r"\b(создай папку|create folder)\s+(.+)$", re.I)
_SHUTDOWN_IN_RE    = re.compile(r"\b(выключи через|shutdown in)\s+(\d+)\s*(?:минут|minutes?|секунд|seconds?)", re.I)
_CONNECT_WIFI_RE   = re.compile(r"\b(подключись к wifi|connect wifi)\s+(.+)$", re.I)
_EXTRACT_RE        = re.compile(r"\b(распакуй|extract)\s+(.+)$", re.I)
_SEARCH_FILES_RE   = re.compile(r"\b(найди в файлах|search in files)\s+(.+)$", re.I)
_CREATE_EVENT_RE   = re.compile(r"\b(создай событие|create event)\s+(.+)$", re.I)
_CREATE_SCENE_RE   = re.compile(r"\b(создай сценарий|create scenario)\s+(.+)$", re.I)
_RUN_SCENE_RE      = re.compile(r"\b(запусти сценарий|run scenario)\s+(.+)$", re.I)
_START_SVC_RE      = re.compile(r"\b(запусти службу|start service)\s+(.+)$", re.I)
_STOP_SVC_RE       = re.compile(r"\b(останови службу|stop service)\s+(.+)$", re.I)
_MOVE_FILE_RE      = re.compile(r"\b(перемести|move)\s+(.+?)\s+(?:в|to)\s+(.+)$", re.I)
_RENAME_FILE_RE    = re.compile(r"\b(переименуй|rename)\s+(.+?)\s+(?:в|to)\s+(.+)$", re.I)
_TYPE_TEXT_RE      = re.compile(r"\b(напиши|введи|type)\s+(.+)$", re.I)
_PRESS_KEY_RE      = re.compile(r"\b(нажми|press)\s+(.+)$", re.I)
_NEWS_TOPIC_RE     = re.compile(r"\b(новости|news)\s+(.+)$", re.I)


@lru_cache(maxsize=256)
def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


@lru_cache(maxsize=128)
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

    # ── Составные команды: открыть приложение + открыть приложение ─────
    compound_app_app = re.search(
        r"(?:открой|запусти|open|launch)\s+(.+?)\s+(?:и|and|затем|then|оттуда|потом)\s+(?:открой|запусти|open|launch)\s+(.+)$",
        raw, re.I
    )
    if compound_app_app:
        app1 = compound_app_app.group(1).strip()
        app2 = compound_app_app.group(2).strip()
        internal1 = _resolve_app(app1)
        internal2 = _resolve_app(app2)
        label1 = app1 if app1 != internal1 else internal1
        label2 = app2 if app2 != internal2 else internal2
        return f"Открываю {label1} и {label2}, сэр.", [
            {"action": "open_app", "target": internal1},
            {"action": "open_app", "target": internal2}
        ]

    # ── Составные команды: открыть приложение + создать заметку ─────
    # Очень гибкий паттерн для любых сложных фраз с "напиши/запиши/впиши"
    compound_app_note = re.search(
        r"(?:открой|запусти|open|launch)\s+(\S+?).+?(?:напиши|запиши|впиши|write)\s+(.+)$",
        raw, re.I
    )
    if compound_app_note:
        app_name = compound_app_note.group(1).strip()
        note_text = compound_app_note.group(2).strip()
        # Очищаем текст от лишних слов
        note_text = re.sub(r'^(?:там|в нём|в ней|в нем|there|in it)\s+', '', note_text, flags=re.I)
        internal = _resolve_app(app_name)
        label = app_name if app_name != internal else internal
        return f"Открываю {label} и создаю заметку, сэр.", [
            {"action": "open_app", "target": internal},
            {"action": "create_note", "text": note_text}
        ]

    # ── Открыть приложение ────────────────────────────────────────
    app_match = _match_app_open(raw)
    if app_match:
        internal, spoken = app_match
        label = spoken if spoken != internal else internal
        return f"Запускаю {label}, сэр.", [{"action": "open_app", "target": internal}]

    # ── Буфер обмена ────────────────────────────────────────────
    if re.search(r"\b(что в буфере|прочитай буфер|clipboard read)\b", t):
        return "", [{"action": "clipboard_read"}]
    if re.search(r"\b(скопируй|copy to clipboard)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(скопируй|copy to clipboard)\s+(.+)$", raw, re.I)
        if m:
            return "", [{"action": "clipboard_copy", "text": m.group(2).strip()}]
    if re.search(r"\b(очисти буфер|clear clipboard)\b", t):
        return "Очищаю буфер обмена, сэр.", [{"action": "clipboard_clear"}]

    # ── Процессы ─────────────────────────────────────────────────
    if re.search(r"\b(топ процессов|процессы|processes|загрузка процесс)\b", t):
        return "", [{"action": "get_top_processes"}]
    if re.search(r"\b(убей процесс|заверши процесс|kill process)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(убей процесс|заверши процесс|kill process)\s+(.+)$", raw, re.I)
        if m:
            return "", [{"action": "kill_process", "target": m.group(2).strip()}]

    # ── Яркость ───────────────────────────────────────────────────
    if re.search(r"\b(яркост|brightn)\s*(?:на|до|at)?\s*(\d{1,3})\s*(?:%|процент\w*)?", raw, re.I):
        m = re.search(r"\b(яркост|brightn)\s*(?:на|до|at)?\s*(\d{1,3})\s*(?:%|процент\w*)?", raw, re.I)
        if m:
            return "", [{"action": "brightness_set", "level": int(m.group(2))}]
    if re.search(r"\b(ярче|brightness up)\b", t):
        return "", [{"action": "brightness_up"}]
    if re.search(r"\b(темнее|brightness down)\b", t):
        return "", [{"action": "brightness_down"}]
    if re.search(r"\b(какая яркость|brightness level)\b", t):
        return "", [{"action": "brightness_get"}]

    # ── Перевод ──────────────────────────────────────────────────
    if re.search(r"\b(переведи|translate)\s+(.+?)\s+(?:на|to)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(переведи|translate)\s+(.+?)\s+(?:на|to)\s+(.+)$", raw, re.I)
        if m:
            return "", [{"action": "translate", "text": m.group(2).strip(), "target_lang": m.group(3).strip()}]

    # ── Напоминания ─────────────────────────────────────────────
    if re.search(r"\b(напомни|remind)\s+(.+?)\s+(?:в|at)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(напомни|remind)\s+(.+?)\s+(?:в|at)\s+(.+)$", raw, re.I)
        if m:
            return "", [{"action": "add_reminder", "message": m.group(2).strip(), "when": m.group(3).strip()}]
    if re.search(r"\b(какие напоминания|list reminders)\b", t):
        return "", [{"action": "list_reminders"}]
    if re.search(r"\b(удали напоминания|clear reminders)\b", t):
        return "Удаляю все напоминания, сэр.", [{"action": "clear_reminders"}]

    # ── YouTube музыка ────────────────────────────────────────────
    if re.search(r"\b(включи|играй|play)\s+(.+?)\s+(?:на ютубе|youtube|в youtube)\b", raw, re.I):
        m = re.search(r"\b(включи|играй|play)\s+(.+?)\s+(?:на ютубе|youtube|в youtube)\b", raw, re.I)
        if m:
            return "", [{"action": "play_youtube", "query": m.group(2).strip()}]
    if re.search(r"\b(останови музыку|stop music)\b", t):
        return "", [{"action": "stop_music"}]

    # ── Валюта ───────────────────────────────────────────────────
    if re.search(r"\b(\d+)\s*(.+?)\s+(?:в|to)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(\d+)\s*(.+?)\s+(?:в|to)\s+(.+)$", raw, re.I)
        if m and any(cur in m.group(2).lower() for cur in ("доллар", "евро", "рубл", "сум", "$", "usd", "eur", "rub", "uzs")):
            return "", [{"action": "convert_currency", "amount": float(m.group(1)), "from_cur": m.group(2).strip(), "to_cur": m.group(3).strip()}]

    # ── Поиск файлов ────────────────────────────────────────────
    if re.search(r"\b(найди файл|find file)\s+(.+)$", raw, re.I):
        m = re.search(r"\b(найди файл|find file)\s+(.+)$", raw, re.I)
        if m:
            return "", [{"action": "find_file", "name": m.group(2).strip()}]

    # ── GPU ──────────────────────────────────────────────────────
    if re.search(r"\b(видеокарта|gpu|nvidia)\b", t) and "открой" not in t:
        return "", [{"action": "gpu_stats"}]

    # ── Окна ────────────────────────────────────────────────────
    if re.search(r"\b(разверни окно|maximize window)\b", t):
        return "", [{"action": "maximize_window"}]
    if re.search(r"\b(сверни окно|minimize window)\b", t):
        return "", [{"action": "minimize_window"}]
    if re.search(r"\b(переключи окно|switch window|alt tab)\b", t):
        return "", [{"action": "switch_window"}]

    # ── Новости ──────────────────────────────────────────────────
    if re.search(r"\b(новости|news)\b", t):
        m = _NEWS_TOPIC_RE.search(raw)
        topic = m.group(2).strip() if m else ""
        return "", [{"action": "get_news", "topic": topic}]

    # ── Файлы ────────────────────────────────────────────────────
    m = _LIST_FILES_RE.search(raw)
    if m:
        return "", [{"action": "list_files", "path": m.group(2).strip()}]
    m = _DELETE_FILE_RE.search(raw)
    if m:
        return "", [{"action": "delete_file", "path": m.group(2).strip()}]
    m = _CREATE_FOLDER_RE.search(raw)
    if m:
        return "", [{"action": "create_folder", "path": m.group(2).strip()}]

    # ── Таймеры питания ───────────────────────────────────────────
    m = _SHUTDOWN_IN_RE.search(raw)
    if m:
        value = int(m.group(2))
        raw_match = m.group(0).lower()
        seconds = value * 60 if ("минут" in raw_match or "min" in raw_match) else value
        return "", [{"action": "schedule_shutdown", "seconds": seconds}]
    if re.search(r"\b(отмени выключение|cancel shutdown)\b", t):
        return "", [{"action": "cancel_shutdown"}]
    if re.search(r"\b(статус выключения|shutdown status)\b", t):
        return "", [{"action": "shutdown_status"}]

    # ── Системная информация ───────────────────────────────────────
    if re.search(r"\b(системная информация|system info|инфо системы)\b", t):
        return "", [{"action": "system_info"}]
    if re.search(r"\b(сеть|network|ip)\b", t) and "открой" not in t:
        return "", [{"action": "network_info"}]

    # ── Сценарии ─────────────────────────────────────────────────
    m = _CREATE_SCENE_RE.search(raw)
    if m:
        return "", [{"action": "create_scenario", "name": m.group(2).strip(), "actions": []}]
    m = _RUN_SCENE_RE.search(raw)
    if m:
        return "", [{"action": "run_scenario", "name": m.group(2).strip()}]
    if re.search(r"\b(список сценарие[вй]|list scenarios)\b", t):
        return "", [{"action": "list_scenarios"}]

    # ── Wi-Fi ─────────────────────────────────────────────────────
    if re.search(r"\b(список wifi|wifi сети|list wifi)\b", t):
        return "", [{"action": "list_wifi"}]
    m = _CONNECT_WIFI_RE.search(raw)
    if m:
        return "", [{"action": "connect_wifi", "ssid": m.group(2).strip(), "password": ""}]
    if re.search(r"\b(отключись от wifi|disconnect wifi)\b", t):
        return "", [{"action": "disconnect_wifi"}]
    if re.search(r"\b(статус wifi|wifi статус|wifi status)\b", t):
        return "", [{"action": "wifi_status"}]

    # ── Запись экрана ───────────────────────────────────────────
    if re.search(r"\b(начни запись|start recording|запиши экран)\b", t):
        return "", [{"action": "start_recording"}]
    if re.search(r"\b(останови запись|stop recording)\b", t):
        return "", [{"action": "stop_recording"}]

    # ── Сжатие файлов ───────────────────────────────────────────
    if re.search(r"\b(сожми файлы|compress files)\b", t):
        return "", [{"action": "compress", "files": [], "output": "archive.zip"}]
    m = _EXTRACT_RE.search(raw)
    if m:
        return "", [{"action": "extract", "archive": m.group(2).strip(), "dest": "."}]

    # ── Поиск в файлах ───────────────────────────────────────────
    m = _SEARCH_FILES_RE.search(raw)
    if m:
        return "", [{"action": "search_in_files", "query": m.group(2).strip(), "path": "."}]

    # ── Камера ───────────────────────────────────────────────────
    if re.search(r"\b(сделай фото|take photo|фотография)\b", t):
        return "", [{"action": "take_photo"}]

    # ── Календарь ───────────────────────────────────────────────
    if re.search(r"\b(события календаря|calendar events|расписание)\b", t):
        return "", [{"action": "calendar_events"}]
    m = _CREATE_EVENT_RE.search(raw)
    if m:
        return "", [{"action": "create_event", "subject": m.group(2).strip(), "start": ""}]

    # ── Bluetooth ───────────────────────────────────────────────
    if re.search(r"\b(список bluetooth|bluetooth устройства|list bluetooth)\b", t):
        return "", [{"action": "list_bluetooth"}]
    if re.search(r"\b(включи bluetooth|enable bluetooth)\b", t):
        return "", [{"action": "enable_bluetooth"}]
    if re.search(r"\b(выключи bluetooth|disable bluetooth)\b", t):
        return "", [{"action": "disable_bluetooth"}]

    # ── Display ─────────────────────────────────────────────────
    if re.search(r"\b(расширь экран|extend display|второй монитор)\b", t):
        return "", [{"action": "extend_display"}]
    if re.search(r"\b(дублируй экран|duplicate display)\b", t):
        return "", [{"action": "duplicate_display"}]
    if re.search(r"\b(основной монитор|primary display|set primary)\b", t):
        return "", [{"action": "set_primary_display"}]

    # ── Keyboard ────────────────────────────────────────────────
    m = _TYPE_TEXT_RE.search(raw)
    if m:
        return "", [{"action": "type_text", "text": m.group(2).strip()}]
    m = _PRESS_KEY_RE.search(raw)
    if m:
        key = m.group(2).strip()
        key = re.sub(r'^(?:клавишу|key)\s+', '', key, flags=re.I)
        key = key.replace('плюс', '+')
        return "", [{"action": "press_key", "key": key}]

    # ── OCR ───────────────────────────────────────────────────
    if re.search(r"\b(распознай текст|ocr|recognize text)\b", t):
        return "", [{"action": "ocr_screenshot"}]

    # ── File Operations ─────────────────────────────────────────
    m = _MOVE_FILE_RE.search(raw)
    if m:
        return "", [{"action": "move_file", "src": m.group(2).strip(), "dst": m.group(3).strip()}]
    m = _RENAME_FILE_RE.search(raw)
    if m:
        return "", [{"action": "rename_file", "old": m.group(2).strip(), "new": m.group(3).strip()}]

    # ── Services ───────────────────────────────────────────────
    if re.search(r"\b(список служб|list services)\b", t):
        return "", [{"action": "list_services"}]
    m = _START_SVC_RE.search(raw)
    if m:
        return "", [{"action": "start_service", "name": m.group(2).strip()}]
    m = _STOP_SVC_RE.search(raw)
    if m:
        return "", [{"action": "stop_service", "name": m.group(2).strip()}]

    # ── Disk Cleanup ────────────────────────────────────────────
    if re.search(r"\b(очисти временные|clean temp|temp files)\b", t):
        return "", [{"action": "clean_temp"}]
    if re.search(r"\b(полностью очисти корзину|empty recycle full)\b", t):
        return "", [{"action": "empty_recycle_full"}]

    # ── Power Modes ────────────────────────────────────────────
    if re.search(r"\b(спящий режим|sleep mode|сон)\b", t):
        return "", [{"action": "sleep_mode"}]
    if re.search(r"\b(гибернация|hibernate)\b", t):
        return "", [{"action": "hibernate_mode"}]

    # ── Audio Devices ──────────────────────────────────────────
    if re.search(r"\b(список аудио|audio devices|звуковые устройства)\b", t):
        return "", [{"action": "list_audio_devices"}]

    return None
