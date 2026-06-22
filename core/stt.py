"""
Модуль распознавания речи (STT).
Основной: Vosk (офлайн, быстрый).
Резервный: Google Speech Recognition (онлайн).
"""
import os
import queue
import threading
import json
import time

import sounddevice as sd
import numpy as np


_VOSK_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer
    _VOSK_AVAILABLE = True
except ImportError:
    pass

_SR_AVAILABLE = False
try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    pass


class STTEngine:
    def __init__(self, cfg: dict, log):
        self.cfg     = cfg
        self.log     = log
        self._model  = None
        self._sr_rec = None
        self._mic    = None
        self._mode   = "none"
        self._init()

    def _init(self):
        # Пробуем Vosk (офлайн)
        if _VOSK_AVAILABLE:
            model_path = os.path.join("models", "small")
            if os.path.isdir(model_path):
                try:
                    self._model = Model(model_path)
                    self._mode  = "vosk"
                    self.log.info("STT", "Vosk загружен (офлайн-режим)")
                    return
                except Exception as e:
                    self.log.warn("STT", f"Vosk не загрузился: {e}")

        # Пробуем Google STT (онлайн)
        if _SR_AVAILABLE:
            try:
                self._sr_rec = sr.Recognizer()
                self._sr_rec.pause_threshold          = float(self.cfg["audio"]["silence_timeout"])
                self._sr_rec.energy_threshold         = int(self.cfg["audio"]["energy_threshold"])
                self._sr_rec.dynamic_energy_threshold = False
                self._mic   = sr.Microphone()
                self._mode  = "google"
                self.log.info("STT", "Google STT готов (онлайн-режим)")
                self._calibrate()
                return
            except Exception as e:
                self.log.error("STT", f"Google STT ошибка: {e}")

        self.log.error("STT", "Ни один STT движок не доступен!")

    def _calibrate(self):
        if self._mode == "google" and self._mic:
            self.log.info("STT", "Калибрую микрофон (помолчите 2 сек)...")
            try:
                with self._mic as src:
                    self._sr_rec.adjust_for_ambient_noise(src, duration=2)
                self.log.info("STT", f"Микрофон готов (порог: {self._sr_rec.energy_threshold:.0f})")
            except Exception as e:
                self.log.warn("STT", f"Калибровка не удалась: {e}")

    @property
    def ready(self) -> bool:
        return self._mode != "none"

    def listen(self) -> str | None:
        """Слушает и возвращает распознанный текст или None"""
        if self._mode == "vosk":
            return self._listen_vosk()
        elif self._mode == "google":
            return self._listen_google()
        return None

    # ── Vosk (офлайн) ────────────────────────────────────────────
    def _listen_vosk(self) -> str | None:
        rec       = KaldiRecognizer(self._model, 16000)
        q: queue.Queue = queue.Queue()
        phrase_limit   = float(self.cfg["audio"]["phrase_limit"])
        silence_t      = float(self.cfg["audio"]["silence_timeout"])

        def _callback(indata, frames, time_info, status):
            q.put(bytes(indata))

        text        = None
        silence_cnt = 0
        max_silence = int(silence_t * (16000 / 4000))   # approx chunks
        start_time  = time.time()

        try:
            with sd.RawInputStream(samplerate=16000, blocksize=4000,
                                   dtype="int16", channels=1,
                                   callback=_callback):
                while True:
                    if time.time() - start_time > phrase_limit:
                        break
                    try:
                        data = q.get(timeout=0.1)
                    except queue.Empty:
                        silence_cnt += 1
                        if silence_cnt > max_silence * 3:
                            break
                        continue

                    silence_cnt = 0
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        t = result.get("text", "").strip()
                        if t:
                            text = t
                            break
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if partial:
                            silence_cnt = 0   # есть речь — сбрасываем тишину

        except Exception as e:
            self.log.error("STT", f"Vosk ошибка: {e}")

        if not text:
            final = json.loads(rec.FinalResult()).get("text", "").strip()
            if final:
                text = final

        return text.lower() if text else None

    # ── Google (онлайн) ──────────────────────────────────────────
    def _listen_google(self) -> str | None:
        limit = float(self.cfg["audio"]["phrase_limit"])
        try:
            with self._mic as src:
                audio = self._sr_rec.listen(src, timeout=None,
                                            phrase_time_limit=limit)
            text = self._sr_rec.recognize_google(audio, language="ru-RU")
            return text.lower().strip()
        except Exception:
            return None
