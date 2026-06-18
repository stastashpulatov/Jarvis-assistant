"""
Все действия с ПК.
Умный поиск приложений: словарь известных путей + поиск по реестру + glob по Program Files.
"""
import os
import glob
import subprocess
import webbrowser
import datetime
import time
import threading

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    winreg = None
    _WINREG_AVAILABLE = False


# ── Поиск в реестре Windows (самый надёжный способ) ─────────────

def _find_in_registry(app_name: str) -> str | None:
    """Ищет путь к exe через реестр Windows."""
    if not _WINREG_AVAILABLE:
        return None
    keys_to_check = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]
    candidates = []
    if app_name.endswith(".exe"):
        candidates.append(app_name)
    else:
        candidates.append(app_name + ".exe")
        candidates.append(app_name.replace(" ", "") + ".exe")

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in keys_to_check:
            for exe_name in candidates:
                try:
                    with winreg.OpenKey(hive, f"{key_path}\\{exe_name}") as k:
                        path, _ = winreg.QueryValueEx(k, "")
                        if path and os.path.exists(path):
                            return path
                except (FileNotFoundError, OSError):
                    continue
    return None


def _find_by_name_glob(name: str, search_roots: list[str]) -> str | None:
    """Ищет exe по частичному совпадению имени файла."""
    patterns = [
        name if name.endswith(".exe") else f"{name}.exe",
        f"*{name}*.exe",
    ]
    for base in search_roots:
        if not os.path.isdir(base):
            continue
        for pattern in patterns:
            matches = glob.glob(os.path.join(base, "**", pattern), recursive=True)
            # Предпочитаем exe с точным именем, не служебные
            matches = [m for m in matches if not any(
                x in os.path.basename(m).lower()
                for x in ("uninstall", "setup", "update", "helper", "service", "container")
            )]
            if matches:
                exact = [m for m in matches if os.path.basename(m).lower() == pattern.lower()]
                return exact[0] if exact else matches[0]
    return None


def _find_start_menu_shortcut(app_name: str) -> str | None:
    """Ищет .lnk в меню Пуск и возвращает путь к ярлыку."""
    roots = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    needle = app_name.lower().replace(" ", "")
    for root in roots:
        if not os.path.isdir(root):
            continue
        for lnk in glob.glob(os.path.join(root, "**", "*.lnk"), recursive=True):
            base = os.path.splitext(os.path.basename(lnk))[0].lower().replace(" ", "")
            if needle in base or base in needle:
                return lnk
    return None


def _find_by_glob(patterns: list) -> str | None:
    """Поиск по шаблонам путей."""
    for p in patterns:
        if "*" in p:
            matches = sorted(glob.glob(p))
            if matches:
                return matches[-1]
        elif os.path.exists(p):
            return p
    return None


def _find_exe(internal_name: str) -> str:
    """
    Находит полный путь к exe.
    Порядок поиска: известные пути → реестр → Program Files glob → shell fallback.
    """

    # 1. Системные утилиты — всегда в PATH
    SYSTEM = {"notepad", "explorer", "calc", "cmd", "powershell",
               "taskmgr", "mspaint", "control", "regedit", "snippingtool"}
    if internal_name in SYSTEM:
        return internal_name

    # 2. Известные пути
    lappdata = os.path.expandvars("%LOCALAPPDATA%")
    appdata  = os.path.expandvars("%APPDATA%")
    pf       = os.path.expandvars("%PROGRAMFILES%")
    pf86     = os.path.expandvars("%PROGRAMFILES(X86)%")

    KNOWN: dict[str, list] = {
        "chrome": [
            f"{pf}\\Google\\Chrome\\Application\\chrome.exe",
            f"{pf86}\\Google\\Chrome\\Application\\chrome.exe",
            f"{lappdata}\\Google\\Chrome\\Application\\chrome.exe",
        ],
        "msedge": [
            f"{pf86}\\Microsoft\\Edge\\Application\\msedge.exe",
            f"{pf}\\Microsoft\\Edge\\Application\\msedge.exe",
        ],
        "firefox": [
            f"{pf}\\Mozilla Firefox\\firefox.exe",
            f"{pf86}\\Mozilla Firefox\\firefox.exe",
        ],
        "telegram": [
            f"{appdata}\\Telegram Desktop\\Telegram.exe",
            f"{lappdata}\\Telegram Desktop\\Telegram.exe",
        ],
        "discord": [
            f"{lappdata}\\Discord\\Update.exe",
        ],
        "spotify": [
            f"{appdata}\\Spotify\\Spotify.exe",
            f"{lappdata}\\Spotify\\Spotify.exe",
        ],
        "steam": [
            f"{pf86}\\Steam\\steam.exe",
            f"{pf}\\Steam\\steam.exe",
        ],
        "vlc": [
            f"{pf}\\VideoLAN\\VLC\\vlc.exe",
            f"{pf86}\\VideoLAN\\VLC\\vlc.exe",
        ],
        "zoom": [
            f"{appdata}\\Zoom\\bin\\Zoom.exe",
            f"{lappdata}\\Zoom\\bin\\Zoom.exe",
        ],
        "vscode": [
            f"{lappdata}\\Programs\\Microsoft VS Code\\Code.exe",
            f"{pf}\\Microsoft VS Code\\Code.exe",
        ],
        "winword": [
            f"{pf}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            f"{pf86}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            f"{pf}\\Microsoft Office\\Office16\\WINWORD.EXE",
        ],
        "excel": [
            f"{pf}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            f"{pf86}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        ],
        "powerpnt": [
            f"{pf}\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            f"{pf86}\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
        ],
        "utorrent": [
            f"{appdata}\\uTorrent\\uTorrent.exe",
            f"{pf86}\\uTorrent\\uTorrent.exe",
        ],
        "obs": [
            f"{pf}\\obs-studio\\bin\\64bit\\obs64.exe",
            f"{pf86}\\obs-studio\\bin\\64bit\\obs64.exe",
        ],
        # NVIDIA
        "nvidia": [
            f"{pf}\\NVIDIA Corporation\\NVIDIA App\\CEF\\NVIDIA App.exe",
            f"{pf86}\\NVIDIA Corporation\\NVIDIA App\\CEF\\NVIDIA App.exe",
            f"{pf}\\NVIDIA Corporation\\NVIDIA app\\CEF\\NVIDIA App.exe",
            f"{pf}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
            f"{pf86}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
        ],
        "geforce": [
            f"{pf}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
            f"{pf86}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
        ],
        # Epic Games
        "epicgames": [
            f"{pf}\\Epic Games\\Launcher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe",
            f"{pf86}\\Epic Games\\Launcher\\Portal\\Binaries\\Win32\\EpicGamesLauncher.exe",
            f"{pf}\\Epic Games\\Launcher\\Portal\\Binaries\\Win32\\EpicGamesLauncher.exe",
            f"{lappdata}\\EpicGamesLauncher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe",
        ],
        # Battle.net
        "battle.net": [
            f"{pf86}\\Battle.net\\Battle.net Launcher.exe",
            f"{pf}\\Battle.net\\Battle.net Launcher.exe",
        ],
        # EA App / Origin
        "origin": [
            f"{pf86}\\Origin\\Origin.exe",
            f"{pf}\\Origin\\Origin.exe",
            f"{pf86}\\Electronic Arts\\EA Desktop\\EA Desktop.exe",
        ],
        "uplay": [
            f"{pf86}\\Ubisoft\\Ubisoft Game Launcher\\UbisoftConnect.exe",
            f"{pf}\\Ubisoft\\Ubisoft Game Launcher\\UbisoftConnect.exe",
        ],
        # Printers
        "itunes": [
            f"{pf}\\iTunes\\iTunes.exe",
            f"{pf86}\\iTunes\\iTunes.exe",
        ],
        "skype": [
            f"{lappdata}\\Microsoft\\WindowsApps\\Skype.exe",
            f"{appdata}\\Microsoft\\Skype for Desktop\\Skype.exe",
        ],
        "slack": [
            f"{lappdata}\\slack\\slack.exe",
        ],
        "figma": [
            f"{lappdata}\\Figma\\Figma.exe",
            f"{appdata}\\Figma\\Figma.exe",
        ],
    }

    # 3. Проверяем известные пути
    found = _find_by_glob(KNOWN.get(internal_name, []))
    if found:
        return found

    # 4. Ищем в реестре
    reg = _find_in_registry(internal_name)
    if reg:
        return reg

    # 5. Fuzzy-поиск по имени (NVIDIA App.exe и т.п.)
    search_roots = [pf, pf86, lappdata, appdata]
    fuzzy = _find_by_name_glob(internal_name, search_roots)
    if fuzzy:
        return fuzzy

    # 6. Ярлык в меню Пуск
    lnk = _find_start_menu_shortcut(internal_name)
    if lnk:
        return lnk

    # 7. Glob по всему Program Files (точное имя)
    exe = internal_name if internal_name.endswith(".exe") else internal_name + ".exe"
    for base in search_roots:
        matches = glob.glob(f"{base}\\**\\{exe}", recursive=True)
        if matches:
            return matches[0]

    return ""


# ── Словарь алиасов ──────────────────────────────────────────────

APP_ALIASES: dict[str, str] = {
    # Браузеры
    "chrome":               "chrome",
    "google chrome":        "chrome",
    "хром":                 "chrome",
    "гугл хром":            "chrome",
    "гугл":                 "chrome",
    "edge":                 "msedge",
    "msedge":               "msedge",
    "microsoft edge":       "msedge",
    "эдж":                  "msedge",
    "майкрософт эдж":       "msedge",
    "firefox":              "firefox",
    "файрфокс":             "firefox",
    # Системные
    "notepad":              "notepad",
    "блокнот":              "notepad",
    "ноутбук":              "notepad",   # частая ошибка распознавания
    "explorer":             "explorer",
    "проводник":            "explorer",
    "файловый менеджер":    "explorer",
    "calc":                 "calc",
    "калькулятор":          "calc",
    "cmd":                  "cmd",
    "командная строка":     "cmd",
    "консоль":              "cmd",
    "powershell":           "powershell",
    "taskmgr":              "taskmgr",
    "диспетчер задач":      "taskmgr",
    "диспетчер":            "taskmgr",
    "mspaint":              "mspaint",
    "paint":                "mspaint",
    "паинт":                "mspaint",
    "рисование":            "mspaint",
    # Office
    "word":                 "winword",
    "ворд":                 "winword",
    "microsoft word":       "winword",
    "excel":                "excel",
    "эксель":               "excel",
    "microsoft excel":      "excel",
    "powerpoint":           "powerpnt",
    "поверпойнт":           "powerpnt",
    "презентация":          "powerpnt",
    # Мессенджеры / соцсети
    "telegram":             "telegram",
    "телеграм":             "telegram",
    "discord":              "discord",
    "дискорд":              "discord",
    "zoom":                 "zoom",
    "зум":                  "zoom",
    "skype":                "skype",
    "скайп":                "skype",
    "slack":                "slack",
    "слак":                 "slack",
    # Медиа
    "spotify":              "spotify",
    "спотифай":             "spotify",
    "музыка":               "spotify",
    "vlc":                  "vlc",
    "itunes":               "itunes",
    "айтюнс":               "itunes",
    # Игровые платформы
    "steam":                "steam",
    "стим":                 "steam",
    "epicgames":            "epicgames",
    "epic games":           "epicgames",
    "epic":                 "epicgames",
    "эпик геймс":           "epicgames",
    "эпик":                 "epicgames",
    "battle.net":           "battle.net",
    "battlenet":            "battle.net",
    "баттлнет":             "battle.net",
    "origin":               "origin",
    "ориджин":              "origin",
    "ea":                   "origin",
    "uplay":                "uplay",
    "ubisoft":              "uplay",
    "убисофт":              "uplay",
    # NVIDIA
    "nvidia":               "nvidia",
    "нвидиа":               "nvidia",
    "nvidia app":           "nvidia",
    "geforce":              "geforce",
    "geforce experience":   "geforce",
    "джифорс":              "geforce",
    # Dev
    "vscode":               "vscode",
    "vs code":              "vscode",
    "visual studio code":   "vscode",
    "вс код":               "vscode",
    "код":                  "vscode",
    # Другое
    "obs":                  "obs",
    "utorrent":             "utorrent",
    "торрент":              "utorrent",
    "figma":                "figma",
    "фигма":                "figma",
}


def _get_browser_exe(browser: str | None) -> str | None:
    """Возвращает путь к exe браузера или None для системного по умолчанию."""
    if not browser:
        return None
    internal = APP_ALIASES.get(browser.lower(), browser.lower())
    if internal in ("chrome", "msedge", "firefox"):
        path = _find_exe(internal)
        return path if path and os.path.exists(path) else None
    return None


def _launch(exe: str) -> None:
    """Запускает exe, .lnk или системную команду."""
    if exe.lower().endswith(".lnk"):
        os.startfile(exe)
        return
    if os.path.isabs(exe) and os.path.exists(exe):
        subprocess.Popen([exe], shell=False)
        return
    if exe in ("notepad", "explorer", "calc", "cmd", "powershell",
               "taskmgr", "mspaint", "control", "regedit", "snippingtool"):
        subprocess.Popen([exe], shell=False)
        return
    raise FileNotFoundError(f"Не найден: {exe}")


def open_app(target: str, log) -> str:
    internal = APP_ALIASES.get(target.lower(), target.lower())
    exe      = _find_exe(internal)
    log.info("CMD", f"Открываю: {target!r} -> {internal!r} -> {exe!r}")

    try:
        if internal == "discord":
            upd = os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
            if os.path.exists(upd):
                subprocess.Popen([upd, "--processStart", "Discord.exe"])
                return ""

        if not exe:
            return f"Сэр, не удалось найти {target}. Возможно, приложение не установлено."

        _launch(exe)
        return ""
    except Exception as e:
        log.error("CMD", f"Не могу запустить '{exe}': {e}")
        return f"Сэр, не удалось запустить {target}. Возможно, приложение не установлено."


def open_url(url: str, log, browser: str | None = None) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    browser_exe = _get_browser_exe(browser)
    if browser_exe:
        subprocess.Popen([browser_exe, url])
    else:
        webbrowser.open(url)

    log.info("CMD", f"URL: {url}" + (f" ({browser})" if browser else ""))
    return ""


def open_urls(urls: list, browser: str | None, log) -> str:
    """Открывает несколько вкладок в указанном браузере."""
    if not urls:
        return "Сэр, не указаны адреса для открытия."

    normalized = []
    for u in urls:
        if not u.startswith(("http://", "https://")):
            u = "https://" + u
        normalized.append(u)

    browser_exe = _get_browser_exe(browser) or _get_browser_exe("msedge")
    if browser_exe:
        subprocess.Popen([browser_exe] + normalized)
        log.info("CMD", f"Вкладки ({len(normalized)}): {normalized} -> {browser_exe}")
        return ""

    for u in normalized:
        webbrowser.open(u)
    log.info("CMD", f"Вкладки ({len(normalized)}): {normalized}")
    return ""


def search_web(query: str, log) -> str:
    webbrowser.open("https://www.google.com/search?q=" + query.replace(" ", "+"))
    log.info("CMD", f"Поиск: {query}")
    return ""


def get_system_info(log) -> str:
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.3)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        msg  = (
            f"Отчёт о системе, сэр. "
            f"Процессор: {cpu:.0f} процентов. "
            f"Память: {ram.percent:.0f} процентов, "
            f"{ram.used//1024**3} из {ram.total//1024**3} гигабайт. "
            f"Диск: {disk.free//1024**3} гигабайт свободно."
        )
        log.info("CMD", f"CPU {cpu:.0f}%  RAM {ram.percent:.0f}%  Disk {disk.free//1024**3}GB free")
        return msg
    except Exception as e:
        return "Не удалось получить данные системы, сэр."


def get_time(log) -> str:
    now    = datetime.datetime.now()
    months = ["января","февраля","марта","апреля","мая","июня",
               "июля","августа","сентября","октября","ноября","декабря"]
    return f"Сейчас {now.strftime('%H:%M')}, {now.day} {months[now.month-1]} {now.year} года, сэр."


def take_screenshot(log) -> str:
    try:
        fname = os.path.join(os.path.expanduser("~"), "Desktop",
                             f"jarvis_{int(time.time())}.png")
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
            "$b=New-Object System.Drawing.Bitmap($s.Width,$s.Height);"
            "$g=[System.Drawing.Graphics]::FromImage($b);"
            "$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size);"
            f"$b.Save('{fname}');"
            "$g.Dispose();$b.Dispose()"
        )
        subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=10)
        if os.path.exists(fname):
            log.info("CMD", f"Скриншот: {fname}")
            return "Скриншот сохранён на рабочем столе, сэр."
        return "Не удалось сделать скриншот, сэр."
    except Exception as e:
        return "Ошибка при создании скриншота, сэр."


def _media_key(vk: int):
    try:
        import ctypes
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
    except Exception:
        pass


def _get_endpoint_volume():
    """Возвращает интерфейс громкости Windows или None."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        return device.EndpointVolume
    except Exception:
        return None


def get_volume_level(log) -> str:
    vol = _get_endpoint_volume()
    if not vol:
        return "Сэр, не удалось определить текущую громкость."
    level = int(round(vol.GetMasterVolumeLevelScalar() * 100))
    muted = vol.GetMute()
    if muted:
        return f"Звук выключен, сэр. Уровень был {level} процентов."
    log.info("CMD", f"Volume level: {level}%")
    return f"Текущая громкость {level} процентов, сэр."


def volume_set(level: int, log) -> str:
    vol = _get_endpoint_volume()
    if not vol:
        return "Сэр, не удалось изменить громкость. Установите pycaw: pip install pycaw"
    level = max(0, min(100, int(level)))
    try:
        vol.SetMute(0, None)
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        actual = int(round(vol.GetMasterVolumeLevelScalar() * 100))
        log.info("CMD", f"Volume set: {actual}%")
        return f"Громкость установлена на {actual} процентов, сэр."
    except Exception as e:
        log.error("CMD", f"Volume set failed: {e}")
        return "Сэр, не удалось изменить громкость."


def volume_up(log) -> str:
    _media_key(0xAF)
    return "Увеличиваю громкость, сэр."

def volume_down(log) -> str:
    _media_key(0xAE)
    return "Уменьшаю громкость, сэр."

def volume_mute(log) -> str:
    _media_key(0xAD)
    return "Переключаю звук, сэр."

def media_play_pause(log) -> str:
    _media_key(0xB3)
    return "Переключаю воспроизведение, сэр."

def media_next(log) -> str:
    _media_key(0xB0)
    return "Следующий трек, сэр."

def media_previous(log) -> str:
    _media_key(0xB1)
    return "Предыдущий трек, сэр."

def open_folder(name: str, log) -> str:
    folders = {
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "рабочий стол": os.path.join(os.path.expanduser("~"), "Desktop"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "загрузки": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "документы": os.path.join(os.path.expanduser("~"), "Documents"),
        "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "изображения": os.path.join(os.path.expanduser("~"), "Pictures"),
        "music": os.path.join(os.path.expanduser("~"), "Music"),
        "музыка": os.path.join(os.path.expanduser("~"), "Music"),
        "videos": os.path.join(os.path.expanduser("~"), "Videos"),
        "видео": os.path.join(os.path.expanduser("~"), "Videos"),
    }
    key = name.strip().lower()
    folder = folders.get(key, name)
    folder = os.path.expandvars(os.path.expanduser(folder))
    if not os.path.exists(folder):
        return f"Сэр, папка {name} не найдена."
    os.startfile(folder)
    log.info("CMD", f"Folder: {folder}")
    return ""

def create_note(text: str, log) -> str:
    text = text.strip()
    if not text:
        return "Сэр, заметка пустая."
    folder = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "jarvis_notes.txt")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {text}\n")
    log.info("CMD", f"Note: {path}")
    return "Записал заметку на рабочий стол, сэр."

def start_timer(seconds: int, message: str, log, tts) -> str:
    seconds = max(1, min(int(seconds), 24 * 60 * 60))
    message = (message or "таймер завершён").strip()

    def _done():
        log.info("CMD", f"Timer done: {message}")
        tts.speak(f"Сэр, {message}.")

    timer = threading.Timer(seconds, _done)
    timer.daemon = True
    timer.start()
    minutes = seconds // 60
    if minutes:
        return f"Таймер на {minutes} минут запущен, сэр."
    return f"Таймер на {seconds} секунд запущен, сэр."

def close_app(target: str, log) -> str:
    internal = APP_ALIASES.get(target.lower(), target.lower())
    exe = internal if internal.endswith(".exe") else internal + ".exe"
    r = subprocess.run(f"taskkill /F /IM {exe}", shell=True,
                       capture_output=True, text=True)
    if r.returncode == 0:
        return f"Закрыл {target}, сэр."
    return f"Не нашёл запущенный процесс {target}, сэр."

def shutdown(log) -> str:
    subprocess.run("shutdown /s /t 3", shell=True)
    return "Выключаю компьютер, сэр. До свидания."

def restart(log) -> str:
    subprocess.run("shutdown /r /t 3", shell=True)
    return "Перезагружаю систему, сэр."

def lock(log) -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Блокирую компьютер, сэр."


# ── Iron Man: расширенные возможности ───────────────────────────

def show_desktop(log) -> str:
    """Win+D — показать рабочий стол."""
    try:
        import ctypes
        VK_LWIN, VK_D, KEYEVENTF_KEYUP = 0x5B, 0x44, 0x0002
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        log.info("CMD", "Show desktop")
        return "Рабочий стол, сэр."
    except Exception as e:
        log.error("CMD", f"Show desktop: {e}")
        return "Не удалось свернуть окна, сэр."


def get_battery(log) -> str:
    try:
        import psutil
        bat = psutil.sensors_battery()
        if not bat:
            return "Сэр, это стационарный компьютер — батареи нет."
        pct = int(bat.percent)
        plugged = "от сети" if bat.power_plugged else "от батареи"
        if bat.secsleft > 0 and not bat.power_plugged:
            hrs = bat.secsleft // 3600
            mins = (bat.secsleft % 3600) // 60
            extra = f", примерно {hrs} ч {mins} мин до разряда"
        else:
            extra = ", зарядка активна" if bat.power_plugged else ""
        log.info("CMD", f"Battery {pct}% ({plugged})")
        return f"Заряд батареи {pct} процентов, работа {plugged}{extra}, сэр."
    except Exception:
        return "Не удалось получить данные батареи, сэр."


def get_weather(city: str, log) -> str:
    try:
        import requests
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1&lang=ru"
        r = requests.get(url, timeout=6, headers={"User-Agent": "JARVIS/1.0"})
        r.raise_for_status()
        data = r.json()
        cur = data["current_condition"][0]
        temp = cur["temp_C"]
        feel = cur["FeelsLikeC"]
        desc = cur.get("lang_ru", [{}])[0].get("value") or cur["weatherDesc"][0]["value"]
        hum = cur["humidity"]
        log.info("CMD", f"Weather {city}: {temp}C")
        return (
            f"Погода в {city}, сэр: {desc}, {temp} градусов, "
            f"ощущается как {feel}. Влажность {hum} процентов."
        )
    except Exception as e:
        log.error("CMD", f"Weather error: {e}")
        return f"Сэр, не удалось получить погоду для {city}."


def run_diagnostics(log) -> str:
    """Полная диагностика — как в фильме."""
    parts = ["Диагностика завершена, сэр."]
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.4)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if os.path.exists("C:\\") else "/")
        boot = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_h = int(boot.total_seconds() // 3600)

        parts.append(f"Процессор: {cpu:.0f} процентов.")
        parts.append(
            f"Память: {ram.percent:.0f} процентов, "
            f"{ram.used // 1024**3} из {ram.total // 1024**3} гигабайт."
        )
        parts.append(f"Диск C: {disk.free // 1024**3} гигабайт свободно.")
        parts.append(f"Аптайм системы: {uptime_h} часов.")

        bat = psutil.sensors_battery()
        if bat:
            parts.append(f"Батарея: {int(bat.percent)} процентов.")

        vol = _get_endpoint_volume()
        if vol:
            lvl = int(round(vol.GetMasterVolumeLevelScalar() * 100))
            parts.append(f"Громкость: {lvl} процентов.")

        log.info("CMD", f"Diagnostics OK — CPU {cpu:.0f}% RAM {ram.percent:.0f}%")
    except Exception as e:
        log.error("CMD", f"Diagnostics: {e}")
        parts.append("Часть данных недоступна.")

    return " ".join(parts)


def empty_recycle_bin(log) -> str:
    try:
        import ctypes
        from ctypes import wintypes
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI   = 0x00000002
        SHERB_NOSOUND        = 0x00000004
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        if res == 0:
            log.info("CMD", "Recycle bin emptied")
            return "Корзина очищена, сэр."
        return "Не удалось очистить корзину, сэр."
    except Exception as e:
        log.error("CMD", f"Recycle bin: {e}")
        return "Ошибка при очистке корзины, сэр."
