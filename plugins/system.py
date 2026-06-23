"""Системные плагины - управление компьютером."""
import subprocess
import os
from core.plugin_loader import jarvis_action


@jarvis_action("restart", "Перезагрузка компьютера")
def restart_computer(log) -> str:
    """Перезагружает компьютер."""
    try:
        os.system("shutdown /r /t 0")
        return "Перезагружаю систему, сэр."
    except Exception as e:
        return f"Сэр, не удалось перезагрузить: {e}"


@jarvis_action("shutdown", "Выключение компьютера")
def shutdown_computer(log) -> str:
    """Выключает компьютер."""
    try:
        os.system("shutdown /s /t 0")
        return "Выключаю систему, сэр."
    except Exception as e:
        return f"Сэр, не удалось выключить: {e}"


@jarvis_action("lock", "Блокировка экрана")
def lock_screen(log) -> str:
    """Блокирует экран."""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Блокирую систему, сэр."
    except Exception as e:
        return f"Сэр, не удалось заблокировать: {e}"


@jarvis_action("logoff", "Завершение сеанса")
def logoff(log) -> str:
    """Завершает сеанс пользователя."""
    try:
        os.system("shutdown /l")
        return "Завершаю сеанс, сэр."
    except Exception as e:
        return f"Сэр, не удалось завершить сеанс: {e}"
