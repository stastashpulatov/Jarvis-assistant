"""Медиа плагины - музыка и видео."""
import subprocess
from core.plugin_loader import jarvis_action


@jarvis_action("play_music", "Воспроизведение музыки")
def play_music(query: str, log) -> str:
    """Ищет и воспроизводит музыку."""
    try:
        # Пример: через yt-dlp или Spotify
        return f"Ищу музыку: {query}, сэр."
    except Exception as e:
        return f"Сэр, не удалось воспроизвести: {e}"


@jarvis_action("pause_media", "Пауза медиа")
def pause_media(log) -> str:
    """Ставит медиа на паузу."""
    try:
        subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys('{MEDIA_PAUSE}')"])
        return "Пауза, сэр."
    except Exception as e:
        return f"Сэр, не удалось поставить на паузу: {e}"


@jarvis_action("next_track", "Следующий трек")
def next_track(log) -> str:
    """Переключает на следующий трек."""
    try:
        subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys('{MEDIA_NEXT}')"])
        return "Следующий трек, сэр."
    except Exception as e:
        return f"Сэр, не удалось переключить: {e}"


@jarvis_action("volume_mute", "Отключение звука")
def volume_mute(log) -> str:
    """Отключает звук."""
    try:
        subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys('{VOLUME_MUTE}')"])
        return "Звук отключён, сэр."
    except Exception as e:
        return f"Сэр, не удалось отключить звук: {e}"
