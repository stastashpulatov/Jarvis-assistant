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
        self._sr     = 24000

        # RVC состояние
        self._rvc_available = False
        self._rvc_ready     = False
        self._rvc_pipeline  = None
        self._rvc_hubert    = None
        self._rvc_net_g     = None
        self._rvc_tgt_sr    = 40000
        self._rvc_if_f0     = 1
        self._rvc_version   = "v2"
        self._rvc_file_index = ""
        self._rvc_config    = None
        self._rvc_lock      = threading.Lock()

        self._init_pyttsx3()

        if self.cfg.get("voice", {}).get("engine", "silero") == "silero":
            self._init_silero()

        # Загружаем RVC в фоне только если путь существует
        if RVC_PYTHON.exists() and RVC_MODEL.exists():
            self._rvc_available = True
            self.log.info("TTS", "RVC найден — загружаю модель в фоне...")
            t = threading.Thread(target=self._load_rvc_in_background, daemon=True)
            t.start()
        else:
            self.log.info("TTS", "RVC не настроен — использую голос Silero напрямую")

        self.log.info("TTS", f"Активный движок: {self._mode}"
                              f"{' + RVC (загружается)' if self._rvc_available else ''}")

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

    # ── RVC (in-process) ─────────────────────────────────────────

    def _load_rvc_in_background(self):
        """Загружает модели RVC в памяти процесса (в фоновом потоке)."""
        try:
            rvc_dir = str(RVC_DIR)
            rmvpe_root = os.path.join(rvc_dir, "assets", "rmvpe")
            index_root = os.path.join(rvc_dir, "logs")
            os.makedirs(rmvpe_root, exist_ok=True)
            os.makedirs(index_root, exist_ok=True)
            os.environ["rmvpe_root"] = rmvpe_root
            os.environ["index_root"] = index_root

            # Добавляем rvc_env к пути
            rvc_site = str(PROJECT_DIR / "rvc_env" / "Lib" / "site-packages")
            if rvc_site not in sys.path:
                sys.path.insert(0, rvc_site)
            if rvc_dir not in sys.path:
                sys.path.insert(0, rvc_dir)

            import torch
            import numpy as np
            import soundfile as sf

            saved_cwd = os.getcwd()
            saved_argv = sys.argv.copy()
            os.chdir(rvc_dir)
            sys.argv = [sys.argv[0]]

            try:
                from configs.config import Config
                from infer.lib.infer_pack.models import (
                    SynthesizerTrnMs256NSFsid,
                    SynthesizerTrnMs256NSFsid_nono,
                    SynthesizerTrnMs768NSFsid,
                    SynthesizerTrnMs768NSFsid_nono,
                )
                from infer.modules.vc.pipeline import Pipeline
                from infer.modules.vc.utils import load_hubert

                config = Config()
                model_path = "assets/weights/jarvis.pth"
                index_path = "logs/jarvis/added_jarvis_v2.index"

                cpt = torch.load(model_path, map_location="cpu", weights_only=False)
                tgt_sr = cpt["config"][-1]
                cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
                version = cpt.get("version", "v2")
                if_f0 = cpt.get("f0", 1)

                synth_map = {
                    ("v1", 1): SynthesizerTrnMs256NSFsid,
                    ("v1", 0): SynthesizerTrnMs256NSFsid_nono,
                    ("v2", 1): SynthesizerTrnMs768NSFsid,
                    ("v2", 0): SynthesizerTrnMs768NSFsid_nono,
                }
                net_g = synth_map[(version, if_f0)](*cpt["config"], is_half=config.is_half)
                del net_g.enc_q
                net_g.load_state_dict(cpt["weight"], strict=False)
                net_g.eval().to(config.device)
                net_g = net_g.half() if config.is_half else net_g.float()

                pipeline = Pipeline(tgt_sr, config)
                hubert_model = load_hubert(config)

                file_index = index_path if pathlib.Path(index_path).exists() else ""

                with self._rvc_lock:
                    self._rvc_pipeline   = pipeline
                    self._rvc_hubert     = hubert_model
                    self._rvc_net_g      = net_g
                    self._rvc_tgt_sr     = tgt_sr
                    self._rvc_if_f0      = if_f0
                    self._rvc_version    = version
                    self._rvc_file_index = file_index
                    self._rvc_config     = config
                    self._rvc_ready      = True

                self.log.info("TTS", "RVC модель загружена и готова к работе")

            finally:
                os.chdir(saved_cwd)
                sys.argv = saved_argv

        except Exception as e:
            import traceback
            err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            tb_msg = traceback.format_exc().encode('ascii', errors='replace').decode('ascii')
            self.log.warn("TTS", f"Ошибка загрузки RVC: {err_msg}")
            self.log.warn("TTS", tb_msg)
            self._rvc_available = False

    def _apply_rvc(self, audio_arr):
        """
        Прогоняет numpy audio через RVC in-process.
        Возвращает (converted_array, sr) или (None, None) при ошибке.
        Использует 'pm' (Parselmouth) — работает без доп. загрузки моделей.
        """
        if not self._rvc_ready:
            return None, None

        try:
            import numpy as np
            import soundfile as sf
            import librosa

            with self._rvc_lock:
                pipeline   = self._rvc_pipeline
                hubert     = self._rvc_hubert
                net_g      = self._rvc_net_g
                tgt_sr     = self._rvc_tgt_sr
                if_f0      = self._rvc_if_f0
                version    = self._rvc_version
                file_index = self._rvc_file_index

            # Resample входного аудио до 16000 Hz (нужно RVC)
            audio_16k = librosa.resample(
                np.asarray(audio_arr, dtype=np.float32),
                orig_sr=self._sr,
                target_sr=16000
            )

            # Нормализация
            audio_max = np.abs(audio_16k).max() / 0.95
            if audio_max > 1:
                audio_16k /= audio_max

            pitch_shift = int(self.cfg.get("voice", {}).get("rvc_pitch_shift", 0))

            # Временный файл (нужен pipeline.pipeline для input_audio_path)
            in_fd, in_path = tempfile.mkstemp(suffix=".wav")
            os.close(in_fd)
            sf.write(in_path, audio_16k, 16000)

            try:
                audio_converted = pipeline.pipeline(
                    hubert,
                    net_g,
                    0,           # sid (speaker id)
                    audio_16k,
                    in_path,     # input_audio_path (только для кэша f0)
                    [0, 0, 0],   # times
                    pitch_shift,
                    "pm",        # f0_method: 'pm' быстрый, без загрузки extra моделей
                    file_index,
                    0.75,        # index_rate
                    if_f0,
                    3,           # filter_radius
                    tgt_sr,
                    0,           # resample_sr (0 = без ресемплинга)
                    0.25,        # rms_mix_rate
                    version,
                    0.33,        # protect
                    None,        # f0_file
                )
            finally:
                try:
                    os.remove(in_path)
                except Exception:
                    pass

            # audio_converted — int16 numpy array из pipeline
            import numpy as np
            arr_float = audio_converted.astype(np.float32) / 32768.0
            return arr_float, tgt_sr

        except Exception as e:
            import traceback
            self.log.warn("TTS", f"RVC ошибка: {e}")
            self.log.warn("TTS", traceback.format_exc())
            return None, None

    # ── speak ────────────────────────────────────────────────────

    def speak(self, text: str, stream: bool = False):
        """Озвучивает текст.
        
        stream=True — разбивает на предложения и озвучивает каждое сразу,
        не дожидаясь генерации всего текста. Уменьшает воспринимаемую задержку.
        """
        if not text or not text.strip():
            return
        if stream:
            self._speak_stream(text)
        else:
            with self._lock:
                if self._mode == "silero":
                    self._speak_silero(text)
                else:
                    self._speak_pyttsx3(text)

    def _speak_stream(self, text: str):
        """Озвучивает текст предложение за предложением без блокировки на весь текст."""
        import re as _re
        sentences = [s.strip() for s in _re.split(r'(?<=[.!?…])\s+', text) if s.strip()]
        if not sentences:
            return
        with self._lock:
            for sentence in sentences:
                if self._mode == "silero":
                    self._speak_silero(sentence)
                else:
                    self._speak_pyttsx3(sentence)

    def _play_audio(self, arr, sr):
        """
        Воспроизводит звук, ресэмплируя до 48000 Hz если нужно.
        """
        import sounddevice as sd
        import numpy as np

        target_sr = 48000
        if sr != target_sr:
            try:
                import librosa
                arr_resampled = librosa.resample(
                    np.asarray(arr, dtype=np.float32), orig_sr=sr, target_sr=target_sr
                )
                sd.play(arr_resampled, target_sr)
            except ImportError:
                sd.play(arr, sr)
        else:
            sd.play(arr, sr)
        sd.wait()

    def _speak_silero(self, text: str):
        try:
            import torch

            speaker = self.cfg.get("voice", {}).get("silero_speaker", "aidar")

            # Оптимизация: кэширование модели на GPU + более быстрая речь
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
            if self._rvc_available and self._rvc_ready:
                converted, converted_sr = self._apply_rvc(arr)
                if converted is not None:
                    self._play_audio(converted, converted_sr)
                    return

            # Без RVC - играем напрямую голосом Silero
            self._play_audio(arr, self._sr)

        except Exception as e:
            self.log.warn("TTS", f"Silero speak: {e} -> pyttsx3")
            self._mode = "pyttsx3"
            self._speak_pyttsx3(text)

    # ── pyttsx3 ──────────────────────────────────────────────────

    def _speak_pyttsx3(self, text: str):
        if self._tts:
            try:
                # Оптимизация скорости речи
                self._tts.setProperty('rate', 200)
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                try:
                    import pyttsx3
                    self._tts = pyttsx3.init()
                    self._tts.setProperty('rate', 200)
                    self._tts.say(text)
                    self._tts.runAndWait()
                except Exception:
                    pass
