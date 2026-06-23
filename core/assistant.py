"""
Главный оркестратор Джарвиса.
Связывает STT → wake word → AI → TTS → CommandRouter.
"""
import time

from .config         import load_config
from .logger         import Logger
from .stt            import STTEngine
from .tts            import TTSEngine
from .wakeword       import is_wake, is_deactivate, strip_wake
from .ai             import GeminiAI
from .command_router import CommandRouter
from .local_parser   import try_parse
from .personality    import (
    boot_speech, activation_line, standby_line,
    proactive_line, print_boot_sequence, hud_status,
)


class Assistant:
    def __init__(self, config_path: str = "config.yaml"):
        self.cfg    = load_config(config_path)
        self.log    = Logger(
            min_level=self.cfg["logging"]["level"],
            enabled=self.cfg["logging"]["enabled"],
        )
        self._print_banner()

        self.tts    = TTSEngine(self.cfg, self.log)
        self.stt    = STTEngine(self.cfg, self.log)
        self.ai     = GeminiAI(self.cfg, self.log)
        self.router = CommandRouter(self.log)

        # Запускаем поток напоминаний
        from . import actions as A
        A.start_reminder_thread(self.tts, self.log)

        # Инициализируем звуковые эффекты
        try:
            from . import sound_effects as SE
            self.sound_effects = SE.SoundEffects(self.log)
            self.sound_effects.play_startup()
        except Exception:
            self.sound_effects = None

        # Предзагрузка AI для мгновенного ответа
        self.log.info("INIT", "Предзагрузка AI модели...")
        try:
            self.ai.ask("")  # Тестовый запрос для инициализации
        except:
            pass

        jarvis_cfg = self.cfg.get("jarvis", {})
        self.wakeword        = self.cfg["A"]["wakeword"]
        self.command_timeout = float(self.cfg["A"]["command_timeout"])
        self.idle_timeout    = float(self.cfg["A"]["idle_timeout"])
        self.always_on       = bool(self.cfg["A"].get("always_on", True))
        self.user_name       = jarvis_cfg.get("user_name", "сэр")
        self.boot_animation  = jarvis_cfg.get("boot_animation", True)
        self.proactive       = bool(jarvis_cfg.get("proactive", True))
        self.suggestion_interval = float(jarvis_cfg.get("suggestion_interval", 1200))
        self.focus_minutes   = int(jarvis_cfg.get("focus_minutes", 50))
        self.break_minutes   = int(jarvis_cfg.get("break_minutes", 10))
        self._ctx            = {
            "awaiting_volume": False,
            "awaiting_confirm": False,
            "default_city": jarvis_cfg.get("city", "Moscow"),
        }

    def _print_banner(self):
        w = self.cfg["A"]["wakeword"]
        gold = "\033[93m"
        cyan = "\033[96m"
        reset = "\033[0m"
        print(f"""
{cyan}  ╔══════════════════════════════════════════════════╗
  ║  {gold}J . A . R . V . I . S .{cyan}                        ║
  ║  Just A Rather Very Intelligent System           ║
  ║  {reset}{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{cyan}  ║
  ║       ●  STARK INDUSTRIES  ●  v2.0              ║
  ╚══════════════════════════════════════════════════╝{reset}
""")
        print(f"  Скажите {gold}«{w}»{reset} для активации\n")

    def speak(self, text: str):
        self.log.jarvis(text)
        # Воспроизводим звук активации перед речью
        if self.sound_effects:
            self.sound_effects.play_in_background("activation")
        self.tts.speak(text)

    def _process(self, user_text: str):
        """Локальный парсер первым — Gemini только для сложных фраз."""
        self.log.you(user_text)

        local = try_parse(user_text, self._ctx)
        if local:
            speech, actions = local
            self.log.info("АССИСТЕНТ", "Локальный парсер (мгновенно)")
        else:
            speech, actions = self.ai.ask(user_text)
            if speech and ("не могу" in speech.lower() or "только увелич" in speech.lower()):
                if any(w in user_text.lower() for w in ("звук", "громк", "volume")):
                    self._ctx["awaiting_volume"] = True

        if speech:
            self.speak(speech)

        if actions:
            # Выполняем действия асинхронно для скорости
            import threading
            def run_actions():
                self.router.route_all(actions, self.tts)
            threading.Thread(target=run_actions, daemon=True).start()

    def _maybe_suggest(self, active: bool, last_suggestion_t: float) -> float:
        """Редкие полезные подсказки, когда пользователь молчит."""
        if not self.proactive or not active:
            return last_suggestion_t
        if time.time() - last_suggestion_t < self.suggestion_interval:
            return last_suggestion_t
        self.speak(proactive_line())
        return time.time()

    def run(self):
        if self.boot_animation:
            print_boot_sequence(
                lambda tag, msg: self.log.debug(tag, msg) if self.cfg["logging"]["enabled"] else None
            )

        if not self.stt.ready:
            self.log.error("АССИСТЕНТ", "STT недоступен. Запускаю текстовый режим.")
            self._text_mode()
            return

        self.speak(boot_speech(self.user_name))

        active            = self.always_on
        last_active_t     = time.time()
        last_suggestion_t = time.time()

        if active:
            hud_status(True, self.wakeword)
            print(f"  \033[93m[ВСЕГДА АКТИВЕН]\033[0m Джарвис слушает постоянно. "
                  f"Скажите «отбой» для режима ожидания.\n")

        while True:
            try:
                text = self.stt.listen()

                if not active:
                    if text and is_wake(text, self.wakeword):
                        active        = True
                        last_active_t = time.time()
                        cmd = strip_wake(text, self.wakeword)
                        if cmd:
                            self._process(cmd)
                        else:
                            self.speak(activation_line())
                            hud_status(True, self.wakeword)
                            print(f"  \033[93m[АКТИВЕН]\033[0m Говорите команду. "
                                  f"Скажите «отбой» для сна.\n")
                else:
                    if text:
                        last_active_t = time.time()
                        last_suggestion_t = time.time()
                        if is_deactivate(text):
                            if self.always_on:
                                self.speak("Сэр, постоянный режим активен. Я остаюсь на связи, но буду говорить реже.")
                                hud_status(True, self.wakeword)
                            else:
                                active = False
                                self.speak(standby_line())
                                hud_status(False, self.wakeword)
                                print(f"\n  Скажите \033[92m«{self.wakeword}»\033[0m"
                                      f" для активации\n")
                        else:
                            cmd = strip_wake(text, self.wakeword)
                            if cmd:
                                self._process(cmd)
                            else:
                                self.speak(activation_line())
                    else:
                        last_suggestion_t = self._maybe_suggest(active, last_suggestion_t)
                        if not self.always_on and time.time() - last_active_t > self.idle_timeout:
                            active = False
                            self.speak(standby_line())
                            hud_status(False, self.wakeword)
                            print(f"\n  Скажите \033[92m«{self.wakeword}»\033[0m"
                                  f" для активации\n")

                time.sleep(0.02)

            except KeyboardInterrupt:
                self.speak(f"Отключаюсь, {self.user_name}. До свидания.")
                break
            except Exception as e:
                self.log.error("АССИСТЕНТ", f"Неожиданная ошибка: {e}")
                time.sleep(0.5)

    def _text_mode(self):
        print("\n  Текстовый режим. Введите команду или 'выход'.\n")
        self.speak("Текстовый режим активирован, сэр.")
        while True:
            try:
                text = input("  \033[92m[ВЫ]\033[0m: ").strip()
                if not text:
                    continue
                if text.lower() in ("выход", "exit", "quit"):
                    self.speak("До свидания, сэр.")
                    break
                self._process(text)
            except (KeyboardInterrupt, EOFError):
                self.speak("До свидания, сэр.")
                break
