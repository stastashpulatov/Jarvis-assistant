"""
Звуковые эффекты для JARVIS - кинематографичность.
"""
import os
import threading
import sounddevice as sd
import numpy as np


class SoundEffects:
    """Менеджер звуковых эффектов для JARVIS."""
    
    def __init__(self, log):
        self.log = log
        self._enabled = True
        self._volume = 0.3
        self._sounds_dir = os.path.join(os.path.dirname(__file__), "..", "sounds")
        
        # Создаём директорию для звуков если нет
        os.makedirs(self._sounds_dir, exist_ok=True)
    
    def play_startup(self):
        """Звук запуска системы."""
        if not self._enabled:
            return
        self._play_tone(440, 0.1, 0.3)
        self._play_tone(554, 0.1, 0.3)
        self._play_tone(659, 0.2, 0.3)
    
    def play_activation(self):
        """Звук активации."""
        if not self._enabled:
            return
        self._play_tone(880, 0.05, 0.2)
    
    def play_processing(self):
        """Звук обработки."""
        if not self._enabled:
            return
        self._play_tone(440, 0.03, 0.1)
    
    def play_success(self):
        """Звук успеха."""
        if not self._enabled:
            return
        self._play_tone(523, 0.1, 0.2)
        self._play_tone(659, 0.1, 0.2)
    
    def play_error(self):
        """Звук ошибки."""
        if not self._enabled:
            return
        self._play_tone(200, 0.2, 0.2)
    
    def play_shutdown(self):
        """Звук выключения."""
        if not self._enabled:
            return
        self._play_tone(659, 0.1, 0.3)
        self._play_tone(554, 0.1, 0.3)
        self._play_tone(440, 0.2, 0.3)
    
    def _play_tone(self, frequency: float, duration: float, volume: float):
        """Воспроизводит тон."""
        try:
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t) * volume * self._volume
            
            # Плавное затухание
            fade_len = int(sample_rate * 0.01)
            if len(tone) > fade_len * 2:
                tone[:fade_len] *= np.linspace(0, 1, fade_len)
                tone[-fade_len:] *= np.linspace(1, 0, fade_len)
            
            sd.play(tone.astype(np.float32), sample_rate)
        except Exception as e:
            self.log.debug("SOUND", f"Ошибка воспроизведения: {e}")
    
    def play_in_background(self, sound_name: str):
        """Воспроизводит звук в фоновом потоке."""
        if not self._enabled:
            return
        
        sounds = {
            "startup": self.play_startup,
            "activation": self.play_activation,
            "processing": self.play_processing,
            "success": self.play_success,
            "error": self.play_error,
            "shutdown": self.play_shutdown,
        }
        
        if sound_name in sounds:
            threading.Thread(target=sounds[sound_name], daemon=True).start()
    
    def set_volume(self, volume: float):
        """Устанавливает громкость эффектов (0.0-1.0)."""
        self._volume = max(0.0, min(1.0, volume))
    
    def enable(self, enabled: bool):
        """Включает/выключает звуковые эффекты."""
        self._enabled = enabled
