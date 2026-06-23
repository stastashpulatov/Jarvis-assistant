"""
HUD интерфейс для JARVIS - визуальная информация в терминале.
"""
import time
import threading
from datetime import datetime


class HUD:
    """Простой HUD для отображения статуса JARVIS."""
    
    def __init__(self, log):
        self.log = log
        self._active = False
        self._thread = None
        self._status = "ОЖИДАНИЕ"
        self._last_command = ""
        self._command_time = 0
    
    def start(self):
        """Запускает HUD в отдельном потоке."""
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Останавливает HUD."""
        self._active = False
    
    def set_status(self, status: str):
        """Устанавливает статус."""
        self._status = status
    
    def set_last_command(self, command: str):
        """Устанавливает последнюю команду."""
        self._last_command = command
        self._command_time = time.time()
    
    def _update_loop(self):
        """Основной цикл обновления HUD."""
        while self._active:
            self._render()
            time.sleep(1)
    
    def _render(self):
        """Отрисовывает HUD."""
        cyan = "\033[96m"
        green = "\033[92m"
        yellow = "\033[93m"
        dim = "\033[2m"
        reset = "\033[0m"
        
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        status_color = green if self._status == "АКТИВЕН" else dim
        
        print(f"\r{cyan}[{time_str}]{reset} {status_color}{self._status}{reset} | {dim}JARVIS v2.0{reset}", end="", flush=True)
        
        if self._last_command and time.time() - self._command_time < 5:
            print(f" | {yellow}Последняя: {self._last_command[:30]}{reset}", end="", flush=True)
