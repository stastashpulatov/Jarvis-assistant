"""
TTS для J.A.R.V.I.S. — Python 3.12, CUDA RTX 4060

Pipeline:
  1. Silero v4 — генерирует русскую речь (CUDA)
  2. RVC (rvc_env, отдельное окружение) — конвертирует тембр в голос Джарвиса
  3. pyttsx3 Microsoft Irina — резерв если что-то выше не работает

RVC опционален: если rvc_env/RVC/assets/weights/jarvis.pth не существует,
Джарвис говорит голосом Silero (aidar) без конвертации - всё равно работает.
"""
import os, sys, threading, warnings, pathlib, subprocess, tempfile, time
warnings.filterwarnings("ignore")

PROJECT_DIR = pathlib.Path(__file__).parent.parent
VOICES_DIR  = PROJECT_DIR / "voices"
RVC_PYTHON  = PROJECT_DIR / "rvc_env" / "Scripts" / "python.exe"
RVC_DIR     = PROJECT_DIR / "rvc_env" / "RVC"
RVC_MODEL   = RVC_DIR / "assets" / "weights" / "jarvis.pth"


class TTSEngine:
    def __init__(self, cfg: dict, log):
        self.cfg     = cfg
        self.log     = log
        self._lock   = threading.Lock()
        self._mode   = "none"
        self._model  = None
        self._device = "cpu"
        self._sr     = 24000  # Silero v4 требует [8000, 24000, 48000]; RVC перересэмплирует автоматически
        self._tts    = None

        self._rvc_available = (
            RVC_PYTHON.exists() and RVC_MODEL.exists()
        )
        if self._rvc_available:
            self.log.info("TTS", "RVC найден — голос Джарвиса будет применён")
        else:
            self.log.info("TTS", "RVC не настроен — использую голос Silero напрямую")

        self._init_pyttsx3()
        if self.cfg.get("voice", {}).get("engine", "silero") == "silero":
            self._init_silero()
        self.log.info("TTS", f"Активный движок: {self._mode}"
                              f"{' + RVC' if (self._mode=='silero' and self._rvc_available) else ''}")

    # ── pyttsx3 (резерв) ─────────────────────────────────────────

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            voices = self._tts.getProperty("voices")
            for v in voices:
                if any(k in v.name.lower() for k in
                       ("irina", "russian", "alena", "pavel", "dmitry")):
                    self._tts.setProperty("voice", v.id)
                    self.log.info("TTS", f"pyttsx3 резерв: {v.name}")
                    break
            self._tts.setProperty("rate",   int(self.cfg["voice"]["offline_rate"]))
            self._tts.setProperty("volume", float(self.cfg["voice"]["offline_volume"]))
            self._mode = "pyttsx3"
        except Exception as e:
            self.log.warn("TTS", f"pyttsx3: {e}")

    # ── Silero ───────────────────────────────────────────────────

    def _find_silero_pt(self) -> pathlib.Path | None:
        import torch
        hub_dir = pathlib.Path(torch.hub.get_dir())
        for silero_dir in hub_dir.glob("snakers4_silero*"):
            exact = silero_dir / "src" / "silero" / "model" / "v4_ru.pt"
            if exact.exists():
                return exact
        for silero_dir in hub_dir.glob("snakers4_silero*"):
            for pt in silero_dir.rglob("v4_ru.pt"):
                return pt
        return None

    def _init_silero(self):
        try:
            import torch
            self.log.info("TTS", "Загружаю Silero TTS...")

            device = "cuda" if torch.cuda.is_available() else "cpu"
            if torch.cuda.is_available():
                self.log.info("TTS", f"CUDA: {torch.cuda.get_device_name(0)}")

            pt_path = self._find_silero_pt()
            if not pt_path:
                self.log.info("TTS", "v4_ru.pt не найден, скачиваю через torch.hub...")
                torch.hub.load(
                    "snakers4/silero-models", "silero_tts",
                    language="ru", speaker="v4_ru",
                    trust_repo=True, verbose=False,
                )
                pt_path = self._find_silero_pt()

            if not pt_path:
                raise FileNotFoundError("v4_ru.pt не найден после загрузки")

            importer = torch.package.PackageImporter(str(pt_path))
            model    = importer.load_pickle("tts_models", "model")

            if model is None:
                raise RuntimeError("load_pickle вернул None")

            # .to() работает in-place и возвращает None - не переприсваивать
            result = model.to(device)
            if result is not None:
                model = result

            if hasattr(model, "eval"):
                model.eval()

            if not hasattr(model, "apply_tts"):
                raise RuntimeError(f"Объект без apply_tts: {type(model)}")

            self._model  = model
            self._device = device
            self._mode   = "silero"
            self.log.info("TTS", f"Silero v4 готов [{device}] — русский голос активен")

        except Exception as e:
            self.log.warn("TTS", f"Silero не загрузился: {e}")
            self.log.warn("TTS", "Использую Microsoft Irina (pyttsx3)")

    # ── speak ────────────────────────────────────────────────────

    def speak(self, text: str):
        if not text or not text.strip():
            return
        with self._lock:
            if self._mode == "silero":
                self._speak_silero(text)
            else:
                self._speak_pyttsx3(text)

    def _speak_silero(self, text: str):
        try:
            import torch
            import sounddevice as sd

            speaker = self.cfg.get("voice", {}).get("silero_speaker", "aidar")

            with torch.no_grad():
                audio = self._model.apply_tts(
                    text=text,
                    speaker=speaker,
                    sample_rate=self._sr,
                    put_accent=True,
                    put_yo=True,
                )

            arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio

            # Пробуем пропустить через RVC (голос Джарвиса)
            if self._rvc_available:
                converted = self._apply_rvc(arr)
                if converted is not None:
                    sd.play(converted, self._sr)
                    sd.wait()
                    return

            # Без RVC - играем напрямую
            sd.play(arr, self._sr)
            sd.wait()

        except Exception as e:
            self.log.warn("TTS", f"Silero speak: {e} -> pyttsx3")
            self._mode = "pyttsx3"
            self._speak_pyttsx3(text)

    # ── RVC voice conversion ─────────────────────────────────────

    # ── RVC voice conversion ─────────────────────────────────────

    def _apply_rvc(self, audio_arr):
        """
        Прогоняет аудио через RVC модель Джарвиса используя subprocess.
        Возвращает numpy array или None при ошибке.
        """
        import soundfile as sf
        
        in_fd,  in_path  = tempfile.mkstemp(suffix=".wav")
        out_fd, out_path = tempfile.mkstemp(suffix=".wav")
        os.close(in_fd)
        os.close(out_fd)

        try:
            sf.write(in_path, audio_arr, self._sr)
            
            pitch_shift = str(self.cfg.get("voice", {}).get("rvc_pitch_shift", 0))
            
            # Вызываем RVC через wrapper без argparse конфликтов
            # Важно: установляем переменные окружения ДО импорта RVC модулей
            env = os.environ.copy()
            env.update({
                "rmvpe_root": str(RVC_DIR / "assets" / "rmvpe"),
                "index_root": str(RVC_DIR / "logs"),
            })
            
            result = subprocess.run(
                [str(RVC_PYTHON), 
                 str(PROJECT_DIR / "rvc_wrapper.py"),
                 in_path, out_path, pitch_shift, str(RVC_DIR)],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            
            if result.returncode != 0:
                err_msg = result.stderr.strip()
                if err_msg:
                    self.log.warn("TTS", f"RVC: {err_msg[-100:]}")
                return None
            
            data, sr = sf.read(out_path)
            return data
            
        except subprocess.TimeoutExpired:
            self.log.warn("TTS", "RVC таймаут (60с)")
            return None
        except Exception as e:
            self.log.warn("TTS", f"RVC: {str(e)[:100]}")
            return None
        finally:
            for p in (in_path, out_path):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    # ── pyttsx3 ──────────────────────────────────────────────────

    def _speak_pyttsx3(self, text: str):
        if self._tts:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                try:
                    import pyttsx3
                    self._tts = pyttsx3.init()
                    self._tts.say(text)
                    self._tts.runAndWait()
                except Exception:
                    pass
