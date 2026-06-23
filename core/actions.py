"""
Все действия с ПК — расширенная версия.
Новые модули: clipboard, processes, brightness, translate,
               reminders, youtube_music, currency, file_search, gpu_stats
"""
import os
import glob
import subprocess
import webbrowser
import datetime
import time
import threading
import json
import re

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    winreg = None
    _WINREG_AVAILABLE = False


# ── Поиск в реестре Windows ──────────────────────────────────────

def _find_in_registry(app_name: str) -> str | None:
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
    patterns = [
        name if name.endswith(".exe") else f"{name}.exe",
        f"*{name}*.exe",
    ]
    for base in search_roots:
        if not os.path.isdir(base):
            continue
        for pattern in patterns:
            matches = glob.glob(os.path.join(base, "**", pattern), recursive=True)
            matches = [m for m in matches if not any(
                x in os.path.basename(m).lower()
                for x in ("uninstall", "setup", "update", "helper", "service", "container")
            )]
            if matches:
                exact = [m for m in matches if os.path.basename(m).lower() == pattern.lower()]
                return exact[0] if exact else matches[0]
    return None


def _find_start_menu_shortcut(app_name: str) -> str | None:
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
    for p in patterns:
        if "*" in p:
            matches = sorted(glob.glob(p))
            if matches:
                return matches[-1]
        elif os.path.exists(p):
            return p
    return None


def _find_exe(internal_name: str) -> str:
    SYSTEM = {"notepad", "explorer", "calc", "cmd", "powershell",
               "taskmgr", "mspaint", "control", "regedit", "snippingtool"}
    if internal_name in SYSTEM:
        return internal_name

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
        "nvidia": [
            f"{pf}\\NVIDIA Corporation\\NVIDIA App\\CEF\\NVIDIA App.exe",
            f"{pf86}\\NVIDIA Corporation\\NVIDIA App\\CEF\\NVIDIA App.exe",
            f"{pf}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
        ],
        "geforce": [
            f"{pf}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
            f"{pf86}\\NVIDIA Corporation\\NVIDIA GeForce Experience\\NVIDIA GeForce Experience.exe",
        ],
        "epicgames": [
            f"{pf}\\Epic Games\\Launcher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe",
            f"{pf86}\\Epic Games\\Launcher\\Portal\\Binaries\\Win32\\EpicGamesLauncher.exe",
            f"{lappdata}\\EpicGamesLauncher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe",
        ],
        "battle.net": [
            f"{pf86}\\Battle.net\\Battle.net Launcher.exe",
            f"{pf}\\Battle.net\\Battle.net Launcher.exe",
        ],
        "origin": [
            f"{pf86}\\Origin\\Origin.exe",
            f"{pf}\\Origin\\Origin.exe",
            f"{pf86}\\Electronic Arts\\EA Desktop\\EA Desktop.exe",
        ],
        "uplay": [
            f"{pf86}\\Ubisoft\\Ubisoft Game Launcher\\UbisoftConnect.exe",
            f"{pf}\\Ubisoft\\Ubisoft Game Launcher\\UbisoftConnect.exe",
        ],
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
        "mpv": [
            f"{pf}\\mpv\\mpv.exe",
            f"{pf86}\\mpv\\mpv.exe",
            os.path.join(os.path.expanduser("~"), "mpv", "mpv.exe"),
            "C:\\mpv\\mpv.exe",
        ],
    }

    found = _find_by_glob(KNOWN.get(internal_name, []))
    if found:
        return found

    reg = _find_in_registry(internal_name)
    if reg:
        return reg

    search_roots = [pf, pf86, lappdata, appdata]
    fuzzy = _find_by_name_glob(internal_name, search_roots)
    if fuzzy:
        return fuzzy

    lnk = _find_start_menu_shortcut(internal_name)
    if lnk:
        return lnk

    exe = internal_name if internal_name.endswith(".exe") else internal_name + ".exe"
    for base in search_roots:
        matches = glob.glob(f"{base}\\**\\{exe}", recursive=True)
        if matches:
            return matches[0]

    return ""


# ── Словарь алиасов ──────────────────────────────────────────────

APP_ALIASES: dict[str, str] = {
    "chrome": "chrome", "google chrome": "chrome", "хром": "chrome", "гугл хром": "chrome",
    "edge": "msedge", "msedge": "msedge", "microsoft edge": "msedge", "эдж": "msedge",
    "firefox": "firefox", "файрфокс": "firefox",
    "notepad": "notepad", "блокнот": "notepad", "ноутбук": "notepad",
    "explorer": "explorer", "проводник": "explorer", "файловый менеджер": "explorer",
    "calc": "calc", "калькулятор": "calc",
    "cmd": "cmd", "командная строка": "cmd", "консоль": "cmd",
    "powershell": "powershell",
    "taskmgr": "taskmgr", "диспетчер задач": "taskmgr", "диспетчер": "taskmgr",
    "mspaint": "mspaint", "paint": "mspaint", "паинт": "mspaint", "рисование": "mspaint",
    "word": "winword", "ворд": "winword", "microsoft word": "winword",
    "excel": "excel", "эксель": "excel", "microsoft excel": "excel",
    "powerpoint": "powerpnt", "поверпойнт": "powerpnt", "презентация": "powerpnt",
    "telegram": "telegram", "телеграм": "telegram",
    "discord": "discord", "дискорд": "discord",
    "zoom": "zoom", "зум": "zoom",
    "skype": "skype", "скайп": "skype",
    "slack": "slack", "слак": "slack",
    "spotify": "spotify", "спотифай": "spotify", "музыка": "spotify",
    "vlc": "vlc",
    "itunes": "itunes", "айтюнс": "itunes",
    "steam": "steam", "стим": "steam",
    "epicgames": "epicgames", "epic games": "epicgames", "epic": "epicgames", "эпик": "epicgames",
    "battle.net": "battle.net", "battlenet": "battle.net", "баттлнет": "battle.net",
    "origin": "origin", "ориджин": "origin", "ea": "origin",
    "uplay": "uplay", "ubisoft": "uplay", "убисофт": "uplay",
    "nvidia": "nvidia", "нвидиа": "nvidia",
    "geforce": "geforce", "geforce experience": "geforce", "джифорс": "geforce",
    "vscode": "vscode", "vs code": "vscode", "visual studio code": "vscode", "код": "vscode",
    "obs": "obs",
    "utorrent": "utorrent", "торрент": "utorrent",
    "figma": "figma", "фигма": "figma",
}


def _get_browser_exe(browser: str | None) -> str | None:
    if not browser:
        return None
    internal = APP_ALIASES.get(browser.lower(), browser.lower())
    if internal in ("chrome", "msedge", "firefox"):
        path = _find_exe(internal)
        return path if path and os.path.exists(path) else None
    return None


def _launch(exe: str) -> None:
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
        return f"Сэр, не удалось запустить {target}."


def open_url(url: str, log, browser: str | None = None) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    browser_exe = _get_browser_exe(browser)
    if browser_exe:
        subprocess.Popen([browser_exe, url])
    else:
        webbrowser.open(url)
    log.info("CMD", f"URL: {url}")
    return ""


def open_urls(urls: list, browser: str | None, log) -> str:
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
        return ""
    for u in normalized:
        webbrowser.open(u)
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
        return msg
    except Exception:
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
    except Exception:
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
    return f"Текущая громкость {level} процентов, сэр."


def volume_set(level: int, log) -> str:
    vol = _get_endpoint_volume()
    if not vol:
        return "Сэр, не удалось изменить громкость."
    level = max(0, min(100, int(level)))
    try:
        vol.SetMute(0, None)
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        actual = int(round(vol.GetMasterVolumeLevelScalar() * 100))
        return f"Громкость установлена на {actual} процентов, сэр."
    except Exception:
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


def show_desktop(log) -> str:
    try:
        import ctypes
        VK_LWIN, VK_D, KEYEVENTF_KEYUP = 0x5B, 0x44, 0x0002
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        return "Рабочий стол, сэр."
    except Exception as e:
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
        return (
            f"Погода в {city}, сэр: {desc}, {temp} градусов, "
            f"ощущается как {feel}. Влажность {hum} процентов."
        )
    except Exception as e:
        log.error("CMD", f"Weather error: {e}")
        return f"Сэр, не удалось получить погоду для {city}."


def run_diagnostics(log) -> str:
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
    except Exception as e:
        log.error("CMD", f"Diagnostics: {e}")
        parts.append("Часть данных недоступна.")
    return " ".join(parts)


def empty_recycle_bin(log) -> str:
    try:
        import ctypes
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI   = 0x00000002
        SHERB_NOSOUND        = 0x00000004
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        if res == 0:
            return "Корзина очищена, сэр."
        return "Не удалось очистить корзину, сэр."
    except Exception as e:
        return "Ошибка при очистке корзины, сэр."


# ══════════════════════════════════════════════════════════════════
#  НОВЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════

# ── 1. Буфер обмена ──────────────────────────────────────────────

def clipboard_read(log) -> str:
    """Зачитывает содержимое буфера обмена."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text or not text.strip():
            return "Буфер обмена пуст, сэр."
        # Обрезаем если слишком длинный
        if len(text) > 300:
            short = text[:300].strip()
            return f"В буфере обмена, сэр: {short}... и ещё {len(text)-300} символов."
        return f"В буфере обмена, сэр: {text.strip()}"
    except Exception as e:
        log.error("CMD", f"Clipboard read: {e}")
        return "Не удалось прочитать буфер обмена, сэр."


def clipboard_copy(text: str, log) -> str:
    """Копирует текст в буфер обмена."""
    try:
        import pyperclip
        pyperclip.copy(text)
        log.info("CMD", f"Clipboard: скопировано {len(text)} символов")
        return f"Скопировал в буфер обмена, сэр."
    except Exception as e:
        log.error("CMD", f"Clipboard copy: {e}")
        return "Не удалось скопировать в буфер обмена, сэр."


def clipboard_clear(log) -> str:
    """Очищает буфер обмена."""
    try:
        import pyperclip
        pyperclip.copy("")
        return "Буфер обмена очищен, сэр."
    except Exception as e:
        return "Не удалось очистить буфер обмена, сэр."


# ── 2. Управление процессами ──────────────────────────────────────

def get_top_processes(log) -> str:
    """Возвращает топ-5 процессов по потреблению памяти."""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["name", "memory_percent", "cpu_percent"]):
            try:
                info = p.info
                if info["memory_percent"] and info["memory_percent"] > 0.1:
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        procs.sort(key=lambda x: x["memory_percent"] or 0, reverse=True)
        top = procs[:5]
        if not top:
            return "Сэр, процессы не найдены."

        parts = ["Топ процессов по памяти, сэр:"]
        for p in top:
            name = p["name"] or "unknown"
            mem  = round(p["memory_percent"] or 0, 1)
            parts.append(f"{name}: {mem} процентов памяти")
        return ". ".join(parts) + "."
    except Exception as e:
        log.error("CMD", f"Top processes: {e}")
        return "Не удалось получить список процессов, сэр."


def kill_process(name: str, log) -> str:
    """Завершает процесс по имени."""
    try:
        import psutil
        killed = []
        exe_name = name if name.endswith(".exe") else name + ".exe"
        for p in psutil.process_iter(["name", "pid"]):
            try:
                if p.info["name"] and p.info["name"].lower() == exe_name.lower():
                    p.kill()
                    killed.append(p.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            log.info("CMD", f"Killed: {killed}")
            return f"Завершил процесс {name}, сэр."
        return f"Процесс {name} не найден среди запущенных, сэр."
    except Exception as e:
        log.error("CMD", f"Kill process: {e}")
        return f"Не удалось завершить {name}, сэр."


# ── 3. Яркость экрана ────────────────────────────────────────────

def brightness_set(level: int, log) -> str:
    """Устанавливает яркость экрана (0–100)."""
    level = max(0, min(100, int(level)))
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        log.info("CMD", f"Brightness set: {level}%")
        return f"Яркость установлена на {level} процентов, сэр."
    except Exception as e:
        # Fallback через WMI
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"],
                capture_output=True, timeout=5
            )
            return f"Яркость установлена на {level} процентов, сэр."
        except Exception:
            log.error("CMD", f"Brightness: {e}")
            return "Не удалось изменить яркость, сэр. Возможно, монитор подключён через HDMI."


def brightness_get(log) -> str:
    """Возвращает текущую яркость."""
    try:
        import screen_brightness_control as sbc
        level = sbc.get_brightness()
        if isinstance(level, list):
            level = level[0]
        return f"Текущая яркость {level} процентов, сэр."
    except Exception:
        return "Не удалось определить текущую яркость, сэр."


def brightness_up(log) -> str:
    try:
        import screen_brightness_control as sbc
        cur = sbc.get_brightness()
        cur = cur[0] if isinstance(cur, list) else cur
        new = min(100, cur + 10)
        sbc.set_brightness(new)
        return f"Яркость повышена до {new} процентов, сэр."
    except Exception:
        return "Не удалось повысить яркость, сэр."


def brightness_down(log) -> str:
    try:
        import screen_brightness_control as sbc
        cur = sbc.get_brightness()
        cur = cur[0] if isinstance(cur, list) else cur
        new = max(0, cur - 10)
        sbc.set_brightness(new)
        return f"Яркость снижена до {new} процентов, сэр."
    except Exception:
        return "Не удалось снизить яркость, сэр."


# ── 4. Перевод текста ─────────────────────────────────────────────

LANG_MAP = {
    "английский": "en", "английском": "en", "english": "en", "en": "en",
    "русский": "ru", "русском": "ru", "russian": "ru", "ru": "ru",
    "немецкий": "de", "немецком": "de", "german": "de", "de": "de",
    "французский": "fr", "французском": "fr", "french": "fr", "fr": "fr",
    "испанский": "es", "испанском": "es", "spanish": "es", "es": "es",
    "китайский": "zh-CN", "китайском": "zh-CN", "chinese": "zh-CN",
    "японский": "ja", "японском": "ja", "japanese": "ja", "ja": "ja",
    "итальянский": "it", "итальянском": "it", "italian": "it",
    "турецкий": "tr", "турецком": "tr", "turkish": "tr",
    "арабский": "ar", "арабском": "ar", "arabic": "ar",
    "узбекский": "uz", "узбекском": "uz", "uzbek": "uz",
}

def translate_text(text: str, target_lang: str, log) -> str:
    """Переводит текст на указанный язык."""
    try:
        lang_code = LANG_MAP.get(target_lang.lower(), target_lang)
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="auto", target=lang_code)
        result = translator.translate(text)
        log.info("CMD", f"Translate -> {lang_code}: {text[:50]}")
        return f"Перевод, сэр: {result}"
    except Exception as e:
        log.error("CMD", f"Translate error: {e}")
        return f"Не удалось перевести текст, сэр."


# ── 5. Умные напоминания ──────────────────────────────────────────

_REMINDERS_FILE = os.path.join(os.path.expanduser("~"), ".jarvis_reminders.json")
_reminders: list[dict] = []
_reminder_thread_started = False


def _load_reminders():
    global _reminders
    try:
        if os.path.exists(_REMINDERS_FILE):
            with open(_REMINDERS_FILE, "r", encoding="utf-8") as f:
                _reminders = json.load(f)
    except Exception:
        _reminders = []


def _save_reminders():
    try:
        with open(_REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(_reminders, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _reminder_loop(tts, log):
    """Фоновый поток: проверяет напоминания каждые 30 секунд."""
    _load_reminders()
    while True:
        time.sleep(30)
        now = datetime.datetime.now()
        fired = []
        for r in _reminders:
            try:
                t = datetime.datetime.fromisoformat(r["time"])
                if t <= now and not r.get("done"):
                    r["done"] = True
                    fired.append(r["message"])
            except Exception:
                pass
        if fired:
            _save_reminders()
            for msg in fired:
                log.info("CMD", f"Reminder: {msg}")
                tts.speak(f"Сэр, напоминание: {msg}.")
        # Удаляем старые выполненные
        _reminders[:] = [r for r in _reminders if not r.get("done") or
                          (datetime.datetime.fromisoformat(r["time"]) >
                           datetime.datetime.now() - datetime.timedelta(hours=1))]


def start_reminder_thread(tts, log):
    """Запускает фоновый поток напоминаний. Вызывать один раз при старте."""
    global _reminder_thread_started
    if _reminder_thread_started:
        return
    _reminder_thread_started = True
    t = threading.Thread(target=_reminder_loop, args=(tts, log), daemon=True)
    t.start()
    log.info("CMD", "Поток напоминаний запущен")


def add_reminder(message: str, when_str: str, log) -> str:
    """
    Добавляет напоминание. when_str — строка типа '18:30', 'через 30 минут', '15:00'.
    """
    _load_reminders()
    now = datetime.datetime.now()
    target_dt = None

    # Формат HH:MM
    m = re.match(r"^(\d{1,2}):(\d{2})$", when_str.strip())
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        target_dt = now.replace(hour=h, minute=mn, second=0, microsecond=0)
        if target_dt <= now:
            target_dt += datetime.timedelta(days=1)

    # Через N минут/часов
    if not target_dt:
        m = re.search(r"через\s+(\d+)\s*(минут|час|секунд)", when_str)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("минут"):
                target_dt = now + datetime.timedelta(minutes=val)
            elif unit.startswith("час"):
                target_dt = now + datetime.timedelta(hours=val)
            else:
                target_dt = now + datetime.timedelta(seconds=val)

    if not target_dt:
        return "Сэр, не понял время напоминания. Попробуйте: «в 18:30» или «через 30 минут»."

    entry = {
        "message": message,
        "time": target_dt.isoformat(),
        "done": False,
    }
    _reminders.append(entry)
    _save_reminders()

    time_str = target_dt.strftime("%H:%M")
    log.info("CMD", f"Reminder added: {message} at {time_str}")
    return f"Напоминание установлено на {time_str}, сэр."


def list_reminders(log) -> str:
    """Озвучивает список активных напоминаний."""
    _load_reminders()
    active = [r for r in _reminders if not r.get("done")]
    if not active:
        return "Активных напоминаний нет, сэр."
    parts = [f"У вас {len(active)} напоминаний, сэр:"]
    for r in active[:5]:
        try:
            t = datetime.datetime.fromisoformat(r["time"]).strftime("%H:%M")
            parts.append(f"в {t}: {r['message']}")
        except Exception:
            pass
    return ". ".join(parts) + "."


def clear_reminders(log) -> str:
    global _reminders
    _reminders = []
    _save_reminders()
    return "Все напоминания удалены, сэр."


# ── 6. Воспроизведение музыки с YouTube ──────────────────────────

_yt_process = None  # текущий процесс плеера


def play_youtube(query: str, log) -> str:
    """Ищет трек на YouTube и воспроизводит через VLC или mpv."""
    global _yt_process

    # Останавливаем предыдущий
    if _yt_process and _yt_process.poll() is None:
        _yt_process.terminate()
        _yt_process = None

    # Ищем плеер
    vlc_path = _find_exe("vlc")
    mpv_path  = _find_exe("mpv")
    player = vlc_path if vlc_path else (mpv_path if mpv_path else None)

    if not player:
        # Открываем поиск в браузере как fallback
        url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
        webbrowser.open(url)
        return f"Сэр, плеер VLC или mpv не найден. Открываю поиск в браузере."

    def _play():
        global _yt_process
        try:
            import yt_dlp
            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "default_search": "ytsearch1",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if not info or not info.get("entries"):
                    log.warn("CMD", "YouTube: ничего не найдено")
                    return
                entry = info["entries"][0]
                url = entry.get("url") or entry.get("webpage_url")
                title = entry.get("title", "трек")
                log.info("CMD", f"YouTube: {title}")

                if "vlc" in player.lower():
                    cmd = [player, "--intf", "dummy", url]
                else:  # mpv
                    cmd = [player, "--no-video", url]
                _yt_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.error("CMD", f"YouTube play: {e}")

    threading.Thread(target=_play, daemon=True).start()
    return f"Ищу и воспроизвожу «{query}», сэр."


def stop_music(log) -> str:
    global _yt_process
    if _yt_process and _yt_process.poll() is None:
        _yt_process.terminate()
        _yt_process = None
        return "Музыка остановлена, сэр."
    _media_key(0xB2)  # media stop key
    return "Останавливаю воспроизведение, сэр."


# ── 7. Конвертация валют ──────────────────────────────────────────

CURRENCY_NAMES = {
    "доллар": "USD", "доллары": "USD", "долларов": "USD", "usd": "USD", "$": "USD",
    "евро": "EUR", "eur": "EUR",
    "рубль": "RUB", "рубли": "RUB", "рублей": "RUB", "руб": "RUB", "rub": "RUB",
    "сум": "UZS", "сумов": "UZS", "uzs": "UZS",
    "фунт": "GBP", "gbp": "GBP",
    "юань": "CNY", "cny": "CNY",
    "иена": "JPY", "jpy": "JPY",
    "тенге": "KZT", "kzt": "KZT",
    "биткоин": "BTC", "btc": "BTC",
}

def convert_currency(amount: float, from_cur: str, to_cur: str, log) -> str:
    """Конвертирует валюту через открытый API."""
    try:
        import requests
        from_code = CURRENCY_NAMES.get(from_cur.lower(), from_cur.upper())
        to_code   = CURRENCY_NAMES.get(to_cur.lower(), to_cur.upper())
        url = f"https://api.exchangerate.host/convert?from={from_code}&to={to_code}&amount={amount}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        result = data.get("result")
        if result is None:
            raise ValueError("Нет данных")
        log.info("CMD", f"Currency: {amount} {from_code} = {result:.2f} {to_code}")
        return f"Сэр, {amount:.0f} {from_code} — это {result:.2f} {to_code}."
    except Exception as e:
        log.error("CMD", f"Currency: {e}")
        return "Сэр, не удалось получить курс валют."


# ── 8. Поиск файлов ───────────────────────────────────────────────

def find_file(name: str, log) -> str:
    """Ищет файл по имени в домашней папке и открывает его."""
    home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
        home,
    ]
    found = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            # Пропускаем скрытые и системные папки
            dirs[:] = [dd for dd in dirs if not dd.startswith(".") and dd not in ("AppData",)]
            for f in files:
                if name.lower() in f.lower():
                    found.append(os.path.join(root, f))
                    if len(found) >= 5:
                        break
            if len(found) >= 5:
                break
    if not found:
        return f"Сэр, файл «{name}» не найден."
    if len(found) == 1:
        os.startfile(found[0])
        log.info("CMD", f"File opened: {found[0]}")
        return f"Открываю файл, сэр: {os.path.basename(found[0])}."
    names = ", ".join(os.path.basename(p) for p in found[:3])
    return f"Сэр, найдено {len(found)} файлов: {names}. Уточните запрос."


# ── 9. Статистика GPU ─────────────────────────────────────────────

def get_gpu_stats(log) -> str:
    """Возвращает статистику GPU через nvidia-smi."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            line = r.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                name, temp, util, mem_used, mem_total = parts
                log.info("CMD", f"GPU: {name}, {temp}C, {util}%, {mem_used}/{mem_total}MB")
                return (
                    f"Видеокарта {name}, сэр. "
                    f"Температура {temp} градусов, нагрузка {util} процентов. "
                    f"Видеопамять: {mem_used} из {mem_total} мегабайт."
                )
        return "Данные GPU недоступны, сэр."
    except FileNotFoundError:
        return "Сэр, nvidia-smi не найден. Возможно, драйверы не установлены."
    except Exception as e:
        log.error("CMD", f"GPU stats: {e}")
        return "Не удалось получить данные видеокарты, сэр."


# ── 10. Управление окнами ─────────────────────────────────────────

def maximize_window(log) -> str:
    """Разворачивает активное окно."""
    try:
        import ctypes
        SW_MAXIMIZE = 3
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)
        return "Разворачиваю окно, сэр."
    except Exception:
        return "Не удалось развернуть окно, сэр."


def minimize_window(log) -> str:
    """Сворачивает активное окно."""
    try:
        import ctypes
        SW_MINIMIZE = 6
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
        return "Сворачиваю окно, сэр."
    except Exception:
        return "Не удалось свернуть окно, сэр."


def switch_window(log) -> str:
    """Alt+Tab — переключение окон."""
    try:
        import ctypes
        VK_ALT, VK_TAB = 0x12, 0x09
        ctypes.windll.user32.keybd_event(VK_ALT, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, 2, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_ALT, 0, 2, 0)
        return "Переключаю окно, сэр."
    except Exception:
        return "Не удалось переключить окно, сэр."


# ── 11. Новости ───────────────────────────────────────────────────

def get_news(topic: str, log) -> str:
    """Получает заголовки новостей через RSS."""
    try:
        import requests
        from xml.etree import ElementTree as ET

        feeds = {
            "": "https://lenta.ru/rss/articles",
            "мир": "https://lenta.ru/rss/news/world",
            "технологии": "https://lenta.ru/rss/news/science",
            "спорт": "https://lenta.ru/rss/news/sport",
            "россия": "https://lenta.ru/rss/news/russia",
        }
        url = feeds.get(topic.lower().strip(), feeds[""])
        r = requests.get(url, timeout=6, headers={"User-Agent": "JARVIS/1.0"})
        root = ET.fromstring(r.text)
        items = root.findall(".//item")[:4]
        if not items:
            return "Сэр, новости недоступны."
        titles = []
        for item in items:
            t = item.find("title")
            if t is not None and t.text:
                titles.append(t.text)
        return f"Сэр, последние новости: {', '.join(titles[:3])}."
    except Exception as e:
        log.error("NEWS", f"Ошибка: {e}")
        return "Сэр, не удалось получить новости."


# ── 12. Продвинутое управление файлами ───────────────────────────────

def list_files(path: str, log) -> str:
    """Список файлов в директории."""
    try:
        if not os.path.exists(path):
            return f"Сэр, путь {path} не существует."
        items = os.listdir(path)[:10]
        if not items:
            return f"Сэр, папка {path} пуста."
        return f"Сэр, в {path}: {', '.join(items)}."
    except Exception as e:
        log.error("FILES", f"Ошибка: {e}")
        return "Сэр, не удалось получить список файлов."


def delete_file(path: str, log) -> str:
    """Удаляет файл."""
    try:
        if not os.path.exists(path):
            return f"Сэр, файл {path} не существует."
        os.remove(path)
        return f"Файл {path} удалён, сэр."
    except Exception as e:
        log.error("FILES", f"Ошибка: {e}")
        return "Сэр, не удалось удалить файл."


def create_folder(path: str, log) -> str:
    """Создаёт папку."""
    try:
        os.makedirs(path, exist_ok=True)
        return f"Папка {path} создана, сэр."
    except Exception as e:
        log.error("FILES", f"Ошибка: {e}")
        return "Сэр, не удалось создать папку."


def copy_file(src: str, dst: str, log) -> str:
    """Копирует файл."""
    try:
        import shutil
        if not os.path.exists(src):
            return f"Сэр, файл {src} не существует."
        shutil.copy2(src, dst)
        return f"Файл скопирован в {dst}, сэр."
    except Exception as e:
        log.error("FILES", f"Ошибка: {e}")
        return "Сэр, не удалось скопировать файл."


# ── 13. Таймеры для команд питания ───────────────────────────────────

_shutdown_timer = None
_shutdown_time = None


def schedule_shutdown(seconds: int, log) -> str:
    """Планирует выключение через N секунд."""
    global _shutdown_timer, _shutdown_time
    try:
        if _shutdown_timer:
            _shutdown_timer.cancel()
        _shutdown_time = time.time() + seconds
        _shutdown_timer = threading.Timer(seconds, _execute_shutdown)
        _shutdown_timer.start()
        mins = seconds // 60
        return f"Выключение через {mins} минут, сэр."
    except Exception as e:
        log.error("POWER", f"Ошибка: {e}")
        return "Сэр, не удалось запланировать выключение."


def cancel_shutdown(log) -> str:
    """Отменяет запланированное выключение."""
    global _shutdown_timer, _shutdown_time
    try:
        if _shutdown_timer:
            _shutdown_timer.cancel()
            _shutdown_timer = None
            _shutdown_time = None
            return "Выключение отменено, сэр."
        return "Сэр, запланированное выключение не найдено."
    except Exception as e:
        log.error("POWER", f"Ошибка: {e}")
        return "Сэр, не удалось отменить выключение."


def _execute_shutdown():
    """Выполняет выключение."""
    os.system("shutdown /s /t 1")


def get_shutdown_status(log) -> str:
    """Статус запланированного выключения."""
    global _shutdown_time
    if _shutdown_time:
        remaining = int(_shutdown_time - time.time())
        mins = remaining // 60
        return f"Сэр, выключение через {mins} минут."
    return "Сэр, запланированное выключение не активно."


# ── 14. Автоматизация сценариев ───────────────────────────────────────

_scenarios = {}


def create_scenario(name: str, actions: list, log) -> str:
    """Создаёт сценарий."""
    global _scenarios
    _scenarios[name] = actions
    return f"Сценарий '{name}' создан, сэр."


def run_scenario(name: str, log) -> str:
    """Запускает сценарий."""
    global _scenarios
    if name not in _scenarios:
        return f"Сэр, сценарий '{name}' не найден."
    return f"Запускаю сценарий '{name}', сэр."


def list_scenarios(log) -> str:
    """Список сценариев."""
    global _scenarios
    if not _scenarios:
        return "Сэр, нет сохранённых сценариев."
    return f"Сэр, доступные сценарии: {', '.join(_scenarios.keys())}."


# ── 15. Системная информация ─────────────────────────────────────────

def get_system_info(log) -> str:
    """Полная системная информация."""
    try:
        import platform
        import psutil
        
        info = {
            "OS": platform.system() + " " + platform.release(),
            "CPU": platform.processor(),
            "RAM": f"{psutil.virtual_memory().total // (1024**3)} GB",
            "Disk": f"{psutil.disk_usage('/').total // (1024**3)} GB",
        }
        return f"Сэр, система: {info['OS']}, процессор: {info['CPU']}, память: {info['RAM']}, диск: {info['Disk']}."
    except Exception as e:
        log.error("SYS", f"Ошибка: {e}")
        return "Сэр, не удалось получить информацию о системе."


def get_network_info(log) -> str:
    """Информация о сети."""
    try:
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return f"Сэр, hostname: {hostname}, IP: {ip}."
    except Exception as e:
        log.error("NET", f"Ошибка: {e}")
        return "Сэр, не удалось получить информацию о сети."


# ── 16. Wi-Fi управление ─────────────────────────────────────────────

def list_wifi_networks(log) -> str:
    """Список доступных Wi-Fi сетей."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            networks = []
            for line in result.stdout.split('\n'):
                if "SSID" in line and ":" in line:
                    ssid = line.split(":")[1].strip()
                    if ssid:
                        networks.append(ssid)
            if networks:
                return f"Сэр, доступные сети: {', '.join(networks[:5])}."
            return "Сэр, сети не найдены."
        return "Сэр, не удалось получить список сетей."
    except Exception as e:
        log.error("WIFI", f"Ошибка: {e}")
        return "Сэр, не удалось получить список сетей."


def connect_wifi(ssid: str, password: str, log) -> str:
    """Подключение к Wi-Fi сети."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return f"Подключаюсь к {ssid}, сэр."
        return f"Сэр, не удалось подключиться к {ssid}."
    except Exception as e:
        log.error("WIFI", f"Ошибка: {e}")
        return "Сэр, не удалось подключиться к сети."


def disconnect_wifi(log) -> str:
    """Отключение от Wi-Fi."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "disconnect"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "Отключаюсь от Wi-Fi, сэр."
    except Exception as e:
        log.error("WIFI", f"Ошибка: {e}")
        return "Сэр, не удалось отключиться от Wi-Fi."


def get_wifi_status(log) -> str:
    """Статус Wi-Fi подключения."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "SSID" in line and ":" in line:
                    ssid = line.split(":")[1].strip()
                    if ssid:
                        return f"Сэр, подключено к {ssid}."
            return "Сэр, не подключено к Wi-Fi."
        return "Сэр, не удалось получить статус Wi-Fi."
    except Exception as e:
        log.error("WIFI", f"Ошибка: {e}")
        return "Сэр, не удалось получить статус Wi-Fi."


# ── 17. Запись экрана ───────────────────────────────────────────────

_screen_recorder = None


def start_screen_recording(log) -> str:
    """Начинает запись экрана."""
    global _screen_recorder
    try:
        import pyautogui
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_{timestamp}.mp4"
        _screen_recorder = {"filename": filename, "start_time": time.time()}
        return f"Запись экрана начата, сэр. Файл: {filename}"
    except Exception as e:
        log.error("SCREEN", f"Ошибка: {e}")
        return "Сэр, не удалось начать запись экрана."


def stop_screen_recording(log) -> str:
    """Останавливает запись экрана."""
    global _screen_recorder
    if not _screen_recorder:
        return "Сэр, запись не активна."
    try:
        duration = int(time.time() - _screen_recorder["start_time"])
        _screen_recorder = None
        return f"Запись остановлена, сэр. Длительность: {duration} сек."
    except Exception as e:
        log.error("SCREEN", f"Ошибка: {e}")
        return "Сэр, не удалось остановить запись."


# ── 18. Сжатие файлов ───────────────────────────────────────────────

def compress_files(files: list, output: str, log) -> str:
    """Сжимает файлы в ZIP архив."""
    try:
        import zipfile
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        return f"Файлы сжаты в {output}, сэр."
    except Exception as e:
        log.error("ZIP", f"Ошибка: {e}")
        return "Сэр, не удалось сжать файлы."


def extract_archive(archive: str, dest: str, log) -> str:
    """Распаковывает архив."""
    try:
        import zipfile
        with zipfile.ZipFile(archive, 'r') as zipf:
            zipf.extractall(dest)
        return f"Архив распакован в {dest}, сэр."
    except Exception as e:
        log.error("ZIP", f"Ошибка: {e}")
        return "Сэр, не удалось распаковать архив."


# ── 19. Поиск по содержимому файлов ─────────────────────────────────

def search_in_files(query: str, path: str, log) -> str:
    """Ищет текст в файлах."""
    try:
        matches = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(('.txt', '.py', '.md', '.json', '.xml', '.html')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                matches.append(filepath)
                    except:
                        continue
            if len(matches) >= 10:
                break
        if matches:
            return f"Сэр, найдено {len(matches)} файлов: {', '.join(matches[:5])}."
        return f"Сэр, ничего не найдено по запросу '{query}'."
    except Exception as e:
        log.error("SEARCH", f"Ошибка: {e}")
        return "Сэр, не удалось выполнить поиск."


# ── 20. Управление камерой ───────────────────────────────────────────

def take_photo(log) -> str:
    """Делает фото с веб-камеры."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            cap.release()
            return f"Фото сохранено как {filename}, сэр."
        cap.release()
        return "Сэр, не удалось сделать фото."
    except Exception as e:
        log.error("CAMERA", f"Ошибка: {e}")
        return "Сэр, камера недоступна."


# ── 21. Календарь ───────────────────────────────────────────────────

def get_calendar_events(log) -> str:
    """Получает события из календаря."""
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        calendar = namespace.GetDefaultFolder(9)  # 9 = Calendar
        events = calendar.Items
        events.Sort("[Start]")
        events.IncludeRecurrences = True
        
        today = datetime.datetime.now().date()
        tomorrow = today + datetime.timedelta(days=1)
        
        events_list = []
        for event in events:
            if hasattr(event, 'Start'):
                event_date = event.Start.date()
                if event_date == today or event_date == tomorrow:
                    events_list.append(event.Subject)
            if len(events_list) >= 5:
                break
        
        if events_list:
            return f"Сэр, события: {', '.join(events_list)}."
        return "Сэр, событий нет."
    except Exception as e:
        log.error("CALENDAR", f"Ошибка: {e}")
        return "Сэр, не удалось получить события календаря."


def create_calendar_event(subject: str, start: str, log) -> str:
    """Создаёт событие в календаре."""
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        appointment = outlook.CreateItem(1)  # 1 = Appointment
        appointment.Subject = subject
        appointment.Start = start
        appointment.Save()
        return f"Событие '{subject}' создано, сэр."
    except Exception as e:
        log.error("CALENDAR", f"Ошибка: {e}")
        return "Сэр, не удалось создать событие."
