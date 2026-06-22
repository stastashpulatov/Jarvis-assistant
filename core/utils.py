"""
Утилиты для JARVIS - оптимизации и вспомогательные функции.
"""
import time
import functools
from typing import Callable, Any


def timing_decorator(func: Callable) -> Callable:
    """Декоратор для измерения времени выполнения функции."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result
    return wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    """Декоратор для повторения функции при ошибках."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_error
        return wrapper
    return decorator


def format_bytes(bytes_size: int) -> str:
    """Форматирует размер в байтах в читаемый вид."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_duration(seconds: float) -> str:
    """Форматирует длительность в секундах в читаемый вид."""
    if seconds < 60:
        return f"{seconds:.1f} сек"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{мин} мин {secs} сек"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours} ч {mins} мин"


def sanitize_filename(filename: str) -> str:
    """Удаляет недопустимые символы из имени файла."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


class PerformanceMonitor:
    """Монитор производительности для отслеживания времени операций."""
    
    def __init__(self):
        self._timings = {}
    
    def start(self, operation: str):
        """Начинает замер операции."""
        self._timings[operation] = time.time()
    
    def end(self, operation: str) -> float:
        """Заканчивает замер и возвращает время в секундах."""
        if operation in self._timings:
            elapsed = time.time() - self._timings[operation]
            del self._timings[operation]
            return elapsed
        return 0.0
    
    def measure(self, operation: str):
        """Контекстный менеджер для замера времени."""
        class _MeasureContext:
            def __init__(self, monitor, op):
                self.monitor = monitor
                self.op = op
            
            def __enter__(self):
                self.monitor.start(self.op)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                elapsed = self.monitor.end(self.op)
                if elapsed > 0:
                    pass  # Можно логировать медленные операции
        return _MeasureContext(self, operation)


# Глобальный монитор производительности
perf_monitor = PerformanceMonitor()
