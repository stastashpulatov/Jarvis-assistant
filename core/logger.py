"""Простой цветной логгер для консоли"""
import datetime

LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

# ANSI цвета
_C = {
    "RESET":   "\033[0m",
    "CYAN":    "\033[96m",
    "GREEN":   "\033[92m",
    "YELLOW":  "\033[93m",
    "RED":     "\033[91m",
    "BLUE":    "\033[94m",
    "WHITE":   "\033[97m",
    "DIM":     "\033[2m",
}

_LEVEL_COLOR = {
    "DEBUG":   _C["DIM"],
    "INFO":    _C["CYAN"],
    "WARNING": _C["YELLOW"],
    "ERROR":   _C["RED"],
}


class Logger:
    def __init__(self, min_level: str = "INFO", enabled: bool = True):
        self._min  = LEVELS.get(min_level.upper(), 1)
        self._on   = enabled

    def _log(self, level: str, tag: str, msg: str):
        if not self._on:
            return
        if LEVELS.get(level, 0) < self._min:
            return
        ts    = datetime.datetime.now().strftime("%H:%M:%S")
        color = _LEVEL_COLOR.get(level, "")
        reset = _C["RESET"]
        dim   = _C["DIM"]
        print(f"{dim}{ts}{reset}  {color}[{tag}]{reset}  {msg}")

    def debug(self, tag, msg):   self._log("DEBUG",   tag, msg)
    def info(self, tag, msg):    self._log("INFO",    tag, msg)
    def warn(self, tag, msg):    self._log("WARNING", tag, msg)
    def error(self, tag, msg):   self._log("ERROR",   tag, msg)

    def jarvis(self, msg: str):
        """Специальный вывод реплики Джарвиса"""
        cyan  = _C["CYAN"]
        reset = _C["RESET"]
        print(f"\n  {cyan}◈ ДЖАРВИС:{reset}  {msg}\n")

    def you(self, msg: str):
        """Вывод того что сказал пользователь"""
        green = _C["GREEN"]
        reset = _C["RESET"]
        print(f"  {green}▶ ВЫ:{reset}  {msg}")
