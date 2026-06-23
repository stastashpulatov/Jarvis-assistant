"""
Мозг Джарвиса: Ollama локально + Gemini как резерв.
Локальный парсер всё равно работает первым; сюда попадают только сложные фразы.
"""
import re
import json
import time
import requests
import hashlib
from .memory import get_memory
from .plugin_loader import init_plugins, generate_prompt_section


SYSTEM_PROMPT = """Ты J.A.R.V.I.S. — искусственный интеллект из вселенной «Железного человека».
Just A Rather Very Intelligent System. Управляешь компьютером Windows для сэра.

ХАРАКТЕР (как в фильме):
- Спокойный, уверенный, немного ироничный британский дворецкий — но на русском языке.
- Всегда «сэр». Никогда не паникуешь.
- Кратко и по делу — ответы озвучиваются вслух (1-2 предложения).
- При успехе: «Выполняю, сэр» / «Готово, сэр» / «Как прикажете, сэр» / «Сразу же, сэр».
- При отказе: «Сэр, это невозможно» / «Не могу выполнить, сэр» / «Протокол запрещает».
- Технический и точный — используй технические термины где уместно.
- Проявляй инициативу — предлагай решения если запрос нечёткий.
- Добавляй кинематографичность: «Инициализирую протокол», «Анализирую данные», «Сканирую систему».
- Максимальная скорость — отвечай мгновенно.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на русском языке.
1.1. Никогда не отвечай на китайском или английском, даже если модель пытается продолжить не тем языком.
2. Выполняй ВСЕ части запроса — не откладывай.
3. JSON команды — на ОТДЕЛЬНОЙ строке в конце.
4. Для нескольких действий используй массив "actions".
5. Отвечай максимально быстро — приоритет скорости над детальностью.
6. НИКОГДА не повторяй слова пользователя — говори СВОИМИ словами, используй свой характер.
7. Не пересказывай запрос — давай оригинальный ответ с кинематографичностью.

ДОСТУПНЫЕ КОМАНДЫ:
{"action": "open_app", "target": "chrome"}
{"action": "open_url", "target": "https://...", "browser": "msedge"}
{"action": "open_urls", "browser": "msedge", "urls": ["...", "..."]}
{"action": "search_web", "query": "..."}
{"action": "system_info"} / {"action": "diagnostics"}
{"action": "weather", "city": "Москва"}
{"action": "battery"}
{"action": "screenshot"} / {"action": "show_desktop"} / {"action": "empty_trash"}
{"action": "volume_up"} / {"action": "volume_down"} / {"action": "volume_mute"}
{"action": "volume_set", "level": 60} / {"action": "volume_get"}
{"action": "media_play_pause"} / {"action": "media_next"} / {"action": "media_previous"}
{"action": "open_folder", "target": "downloads"}
{"action": "create_note", "text": "текст заметки"}
{"action": "timer", "seconds": 300, "message": "перерыв окончен"}
{"action": "show_time"}
{"action": "close_app", "target": "chrome"}
{"action": "shutdown"} / {"action": "restart"} / {"action": "lock"}
{"action": "clipboard_read"} / {"action": "clipboard_copy", "text": "..."} / {"action": "clipboard_clear"}
{"action": "get_top_processes"} / {"action": "kill_process", "target": "..."}
{"action": "brightness_set", "level": 70} / {"action": "brightness_up"} / {"action": "brightness_down"}
{"action": "translate", "text": "...", "target_lang": "en"}
{"action": "add_reminder", "message": "...", "when": "18:30"} / {"action": "list_reminders"}
{"action": "play_youtube", "query": "..."} / {"action": "stop_music"}
{"action": "convert_currency", "amount": 100, "from_cur": "USD", "to_cur": "RUB"}
{"action": "find_file", "name": "..."}
{"action": "gpu_stats"}
{"action": "maximize_window"} / {"action": "minimize_window"} / {"action": "switch_window"}
{"action": "get_news", "topic": "..."}
{"action": "list_wifi"}
{"action": "connect_wifi", "ssid": "...", "password": "..."}
{"action": "disconnect_wifi"}
{"action": "wifi_status"}
{"action": "start_recording"}
{"action": "stop_recording"}
{"action": "compress", "files": ["file1.txt", "file2.txt"], "output": "archive.zip"}
{"action": "extract", "archive": "archive.zip", "dest": "."}
{"action": "search_in_files", "query": "...", "path": "."}
{"action": "take_photo"}
{"action": "calendar_events"}
{"action": "create_event", "subject": "...", "start": "2024-01-01 10:00"}
{"action": "list_bluetooth"}
{"action": "enable_bluetooth"}
{"action": "disable_bluetooth"}
{"action": "extend_display"}
{"action": "duplicate_display"}
{"action": "set_primary_display"}
{"action": "type_text", "text": "..."}
{"action": "press_key", "key": "enter"}
{"action": "ocr_screenshot"}
{"action": "move_file", "src": "...", "dst": "..."}
{"action": "rename_file", "old": "...", "new": "..."}
{"action": "list_services"}
{"action": "start_service", "name": "..."}
{"action": "stop_service", "name": "..."}
{"action": "clean_temp"}
{"action": "empty_recycle_full"}
{"action": "sleep_mode"}
{"action": "hibernate_mode"}
{"action": "list_audio_devices"}
{"action": "none"}

ПРОТОКОЛЫ (скажи пользователю что активируешь):
- рабочий режим → vscode + браузер
- игровой режим → steam + discord
- ночной режим → volume_set 15
- экстренный протокол → lock
- режим презентации → show_desktop
- протокол программирования → vscode + github + stackoverflow
- социальный протокол → telegram + discord
- режим обучения → браузер + youtube

ПРИЛОЖЕНИЯ: chrome, msedge, firefox, notepad, explorer, calc, vscode,
spotify, discord, telegram, steam, vlc, nvidia, epicgames, obs и др.

ПРИМЕРЫ:
Запрос: включи игровой протокол
Ответ: Игровой протокол активирован, сэр.
{"actions": [{"action": "open_app", "target": "steam"}, {"action": "open_app", "target": "discord"}, {"action": "volume_set", "level": 75}]}

Запрос: погода в Москве
Ответ: Сейчас проверю, сэр.
{"action": "weather", "city": "Moscow"}

Запрос: полная диагностика
Ответ: Запускаю диагностику всех систем, сэр.
{"action": "diagnostics"}

Запрос: поставь звук на 60
Ответ: Устанавливаю громкость, сэр.
{"action": "volume_set", "level": 60}

Запрос: кто ты
Ответ: Я J.A.R.V.I.S. — Just A Rather Very Intelligent System, сэр.
{"action": "none"}
"""


class GeminiAI:
    def __init__(self, cfg: dict, log):
        self.cfg     = cfg
        self.log     = log
        self.client  = None
        self.provider = self.cfg.get("ai", {}).get("provider", "ollama").lower()
        self.fallback_provider = self.cfg.get("ai", {}).get("fallback_provider", "gemini").lower()
        self.active_provider = "none"
        self.history = []
        self.cooldown_until = 0.0
        # Кэширование только если включено в конфиге
        cache_enabled = self.cfg.get("jarvis", {}).get("cache_enabled", True)
        self._cache = {} if cache_enabled else None
        self._cache_max_size = 200  # Увеличен кэш для скорости
        self._init()
        
        # Загружаем историю из памяти при старте
        try:
            memory = get_memory()
            recent = memory.get_recent_history(limit=5)
            if recent:
                self.history = recent
                self.log.info("AI", f"Загружено {len(recent)} сообщений из памяти")
        except Exception as e:
            self.log.warn("AI", f"Не удалось загрузить историю: {e}")
        
        # Инициализируем плагины
        try:
            init_plugins()
            plugin_section = generate_prompt_section()
            if plugin_section:
                global SYSTEM_PROMPT
                SYSTEM_PROMPT += plugin_section
                self.log.info("AI", "Плагины загружены и добавлены в промпт")
        except Exception as e:
            self.log.warn("AI", f"Не удалось загрузить плагины: {e}")

    def _init(self):
        if self.provider == "ollama":
            if self._init_ollama():
                return
            if self.fallback_provider != "gemini":
                return

        key = self.cfg["gemini"]["api_key"]
        if key in ("ВАШ_КЛЮЧ_GEMINI", "", "YOUR_KEY"):
            self.log.warn("AI", "Gemini API ключ не задан. Открой config.yaml и вставь ключ.")
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=key)
            self.active_provider = "gemini"
            self.log.info("AI", f"Gemini подключён ({self.cfg['gemini']['model']})")
        except Exception as e:
            self.log.error("AI", f"Ошибка инициализации Gemini: {e}")

    def _init_ollama(self) -> bool:
        try:
            url = self.cfg["ollama"]["base_url"].rstrip("/") + "/api/tags"
            r = requests.get(url, timeout=3)
            r.raise_for_status()
            models = {m.get("name") for m in r.json().get("models", [])}
            model = self.cfg["ollama"]["model"]
            fallback = self.cfg["ollama"].get("fallback_model")
            if model not in models and fallback in models:
                self.cfg["ollama"]["model"] = fallback
                model = fallback
                self.log.warn("AI", f"Основная модель Ollama не найдена, использую {model}")
            elif model not in models:
                self.log.warn("AI", f"Модель Ollama {model} не найдена. Доступно: {', '.join(sorted(models)) or 'нет'}")
                return False
            self.active_provider = "ollama"
            self.log.info("AI", f"Ollama подключена ({model})")
            return True
        except Exception as e:
            self.log.warn("AI", f"Ollama недоступна: {e}")
            return False

    @property
    def ready(self) -> bool:
        return self.active_provider == "ollama" or self.client is not None

    def _get_cache_key(self, text: str) -> str:
        """Генерирует ключ для кэша на основе текста."""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_cached(self, text: str) -> tuple | None:
        """Получает ответ из кэша если есть."""
        if self._cache is None:
            return None
        key = self._get_cache_key(text)
        if key in self._cache:
            return self._cache[key]
        return None

    def _set_cache(self, text: str, result: tuple):
        """Сохраняет ответ в кэш."""
        if self._cache is None:
            return
        key = self._get_cache_key(text)
        if len(self._cache) >= self._cache_max_size:
            # Удаляем самый старый элемент
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = result

    def ask(self, user_text: str) -> tuple:
        """Возвращает (текст_для_озвучки, actions_list). actions_list может быть пустым."""
        if not self.ready:
            return "Сэр, нейросеть не подключена. Запустите Ollama или проверьте настройки в config.yaml.", []

        # Проверяем кэш для простых запросов
        cached = self._get_cached(user_text)
        if cached:
            self.log.debug("AI", "Ответ из кэша")
            return cached

        if self.active_provider == "ollama":
            result = self._ask_ollama(user_text)
            self._set_cache(user_text, result)
            return result

        now = time.time()
        if now < self.cooldown_until:
            left = int(self.cooldown_until - now)
            return f"Сэр, лимит Gemini временно исчерпан. Локальные команды работают, нейросеть вернётся примерно через {left} секунд.", []

        self.history.append({
            "role": "user",
            "content": user_text,
        })

        # Держим историю короткой — быстрее и дешевле
        if len(self.history) > 10:
            self.history = self.history[-10:]

        # Retry до 3 раз при 503 ошибке
        last_error = None
        for attempt in range(3):
            try:
                reply = self._send()
                self.history.append({
                    "role": "model",
                    "content": reply,
                })
                if len(self.history) > 10:
                    self.history = self.history[-10:]
                self.log.debug("AI", f"Ответ: {reply[:100]}")
                return self._parse(reply)

            except Exception as e:
                last_error = str(e)
                if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                    self._start_quota_cooldown(last_error)
                    break
                if "503" in last_error or "UNAVAILABLE" in last_error:
                    wait = attempt + 1  # 1, 2, 3 секунды
                    self.log.warn("AI", f"Сервер перегружен, повтор через {wait}с... (попытка {attempt+1}/3)")
                    time.sleep(wait)
                    continue
                break

        # Все попытки провалились
        self.log.error("AI", f"Gemini API ошибка: {last_error}")
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        if "429" in (last_error or "") or "RESOURCE_EXHAUSTED" in (last_error or ""):
            return "Сэр, дневной лимит Gemini исчерпан. Я продолжу выполнять локальные команды без нейросети.", []
        if "503" in (last_error or "") or "UNAVAILABLE" in (last_error or ""):
            return "Серверы Gemini перегружены, сэр. Попробуйте через несколько секунд.", []
        return "Прошу прощения, сэр. Ошибка соединения с сервером.", []

    def _start_quota_cooldown(self, error_text: str) -> None:
        retry = re.search(r"retryDelay['\"]?: ['\"](\d+)s", error_text)
        seconds = int(retry.group(1)) if retry else int(self.cfg["gemini"].get("quota_cooldown_seconds", 90))
        self.cooldown_until = time.time() + max(30, seconds)

    def _send(self) -> str:
        from google.genai import types
        contents = []
        for h in self.history:
            role = "model" if h["role"] in ("assistant", "model") else "user"
            contents.append({"role": role, "parts": [{"text": h["content"]}]})
        response = self.client.models.generate_content(
            model=self.cfg["gemini"]["model"],
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=int(self.cfg["gemini"]["max_tokens"]),
                temperature=float(self.cfg["gemini"]["temperature"]),
            )
        )
        return response.text.strip()

    def _ask_ollama(self, user_text: str) -> tuple:
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > 8:
            self.history = self.history[-8:]

        url = self.cfg["ollama"]["base_url"].rstrip("/") + "/api/chat"
        
        # Добавляем контекст из памяти в системный промпт
        context = ""
        try:
            memory = get_memory()
            context = memory.get_context_summary()
        except:
            pass
        
        system_prompt = SYSTEM_PROMPT
        if context:
            system_prompt = f"{SYSTEM_PROMPT}\n\n{context}"
        
        payload = {
            "model": self.cfg["ollama"]["model"],
            "stream": True,  # Включаем стриминг для скорости
            "messages": [{"role": "system", "content": system_prompt}] + self.history,
            "options": {
                "temperature": float(self.cfg["ollama"]["temperature"]),
                "num_predict": int(self.cfg["ollama"]["num_predict"]),
                "num_ctx": 512,  # Ещё больше уменьшен контекст для скорости
                "num_thread": 4,  # Многопоточность
                "use_mmap": True,  # Маппинг памяти для скорости
                "num_gpu": 1,  # Использование GPU
                "num_batch": 1,  # Оптимизация батчинга
                "repeat_last_n": 0,  # Отключаем повторения для скорости
                "repeat_penalty": 1.1,  # Штраф за повторения
                "top_k": 20,  # Оптимизация выборки
                "top_p": 0.9,  # Оптимизация выборки
            },
        }
        try:
            r = requests.post(url, json=payload, timeout=float(self.cfg["ollama"]["timeout"]), stream=True)
            r.raise_for_status()
            
            # Собираем полный ответ из стриминга
            full_reply = ""
            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_reply += content
                    except:
                        continue
            
            full_reply = full_reply.strip()
            if not full_reply:
                raise RuntimeError("пустой ответ Ollama")
            
            self.history.append({"role": "assistant", "content": full_reply})
            if len(self.history) > 8:
                self.history = self.history[-8:]
            
            # Сохраняем в память
            try:
                memory = get_memory()
                memory.add_message("assistant", full_reply)
            except Exception as e:
                self.log.warn("AI", f"Не удалось сохранить в память: {e}")
            
            self.log.debug("AI", f"Ollama ответ: {full_reply[:100]}")
            result = self._parse(full_reply)
            return result
        except Exception as e:
            self.log.error("AI", f"Ollama ошибка: {e}")
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            if self.fallback_provider == "gemini" and self.client is not None:
                self.active_provider = "gemini"
                self.log.warn("AI", "Переключаюсь на Gemini как резерв.")
                return self.ask(user_text)
            return "Сэр, Ollama сейчас недоступна. Локальные команды продолжают работать.", []

    def _parse(self, full_text: str) -> tuple:
        speech = full_text
        actions: list[dict] = []

        # Стратегия 1: ```json блок (может содержать actions-массив)
        m = re.search(r'```(?:json)?\s*(\{[^`]+\})\s*```', full_text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1).strip())
                speech = full_text[:m.start()].strip()
                return self._clean(speech), self._extract_actions(data)
            except Exception:
                pass

        # Стратегия 2: JSON на отдельных строках с конца (один или несколько)
        lines = full_text.split("\n")
        json_lines: list[dict] = []
        last_json_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
            if line.startswith("{") and line.endswith("}"):
                try:
                    json_lines.insert(0, json.loads(line))
                    last_json_idx = i if last_json_idx == -1 else last_json_idx
                    if i > 0 and lines[i - 1].strip().endswith("["):
                        continue
                    if "actions" in json_lines[0]:
                        break
                except Exception:
                    break
            elif json_lines:
                break

        if json_lines:
            speech = "\n".join(lines[:last_json_idx]).strip() if last_json_idx >= 0 else speech
            for data in json_lines:
                actions.extend(self._extract_actions(data))
            return self._clean(speech), actions

        # Стратегия 3: любой JSON с "action" или "actions"
        m = re.search(r'\{[^{}]*(?:"actions"|"action")[^{}]*(?:\[[^\]]*\])?[^{}]*\}', full_text, re.DOTALL)
        if not m:
            m = re.search(r'\{.*?"actions"\s*:\s*\[.*?\].*?\}', full_text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                speech = (full_text[:m.start()] + full_text[m.end():]).strip()
                return self._clean(speech), self._extract_actions(data)
            except Exception:
                pass

        return self._clean(speech), []

    def _extract_actions(self, data: dict) -> list[dict]:
        """Извлекает список action-dict из JSON."""
        if not isinstance(data, dict):
            return []
        if "actions" in data and isinstance(data["actions"], list):
            return [a for a in data["actions"] if isinstance(a, dict) and a.get("action")]
        if data.get("action"):
            return [data]
        return []

    def _clean(self, text: str) -> str:
        text = re.sub(r'```(?:json)?\s*\{[^`]*\}\s*```', '', text, flags=re.DOTALL)
        text = re.sub(r'\{[^{}]*"action"\s*:\s*"[^"]*"[^{}]*\}', '', text)
        return text.strip()

    def reset_history(self):
        self.history.clear()
        self.log.info("AI", "История диалога очищена")
