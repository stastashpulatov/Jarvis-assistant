"""Маршрутизатор команд: получает action dict → вызывает нужную функцию"""
from . import actions as A


class CommandRouter:
    def __init__(self, log):
        self.log = log

    def route_all(self, actions: list[dict], tts) -> None:
        """Выполняет список команд по порядку."""
        for action in actions:
            if action.get("action", "none") != "none":
                self.route(action, tts)

    def route(self, action: dict, tts) -> None:
        """Выполняет одну команду. tts — для дополнительных сообщений (ошибки, результаты)."""
        act = action.get("action", "none")
        self.log.info("РОУТЕР", f"Команда: {action}")

        msg = ""

        if act == "open_app":
            msg = A.open_app(action.get("target", ""), self.log)

        elif act == "open_url":
            msg = A.open_url(
                action.get("target", ""),
                self.log,
                browser=action.get("browser"),
            )

        elif act == "open_urls":
            msg = A.open_urls(
                action.get("urls", []),
                action.get("browser"),
                self.log,
            )

        elif act == "search_web":
            msg = A.search_web(action.get("query", ""), self.log)

        elif act == "system_info":
            msg = A.get_system_info(self.log)

        elif act == "show_time":
            msg = A.get_time(self.log)

        elif act == "screenshot":
            msg = A.take_screenshot(self.log)

        elif act == "volume_up":
            msg = A.volume_up(self.log)

        elif act == "volume_down":
            msg = A.volume_down(self.log)

        elif act == "volume_mute":
            msg = A.volume_mute(self.log)

        elif act == "volume_set":
            msg = A.volume_set(int(action.get("level", 50)), self.log)

        elif act == "volume_get":
            msg = A.get_volume_level(self.log)

        elif act == "media_play_pause":
            msg = A.media_play_pause(self.log)

        elif act == "media_next":
            msg = A.media_next(self.log)

        elif act == "media_previous":
            msg = A.media_previous(self.log)

        elif act == "open_folder":
            msg = A.open_folder(action.get("target", ""), self.log)

        elif act == "create_note":
            msg = A.create_note(action.get("text", ""), self.log)

        elif act == "timer":
            msg = A.start_timer(
                int(action.get("seconds", 60)),
                action.get("message", "таймер завершён"),
                self.log,
                tts,
            )

        elif act == "close_app":
            msg = A.close_app(action.get("target", ""), self.log)

        elif act == "shutdown":
            msg = A.shutdown(self.log)

        elif act == "restart":
            msg = A.restart(self.log)

        elif act == "lock":
            msg = A.lock(self.log)

        elif act == "diagnostics":
            msg = A.run_diagnostics(self.log)

        elif act == "weather":
            msg = A.get_weather(action.get("city", "Moscow"), self.log)

        elif act == "battery":
            msg = A.get_battery(self.log)

        elif act == "show_desktop":
            msg = A.show_desktop(self.log)

        elif act == "empty_trash":
            msg = A.empty_recycle_bin(self.log)

        # ── Clipboard ─────────────────────────────────────────────────
        elif act == "clipboard_read":
            msg = A.clipboard_read(self.log)

        elif act == "clipboard_copy":
            msg = A.clipboard_copy(action.get("text", ""), self.log)

        elif act == "clipboard_clear":
            msg = A.clipboard_clear(self.log)

        # ── Processes ─────────────────────────────────────────────────
        elif act == "get_top_processes":
            msg = A.get_top_processes(self.log)

        elif act == "kill_process":
            msg = A.kill_process(action.get("target", ""), self.log)

        # ── Brightness ────────────────────────────────────────────────
        elif act == "brightness_set":
            msg = A.brightness_set(int(action.get("level", 50)), self.log)

        elif act == "brightness_get":
            msg = A.brightness_get(self.log)

        elif act == "brightness_up":
            msg = A.brightness_up(self.log)

        elif act == "brightness_down":
            msg = A.brightness_down(self.log)

        # ── Translate ─────────────────────────────────────────────────
        elif act == "translate":
            msg = A.translate_text(
                action.get("text", ""),
                action.get("target_lang", "en"),
                self.log
            )

        # ── Reminders ─────────────────────────────────────────────────
        elif act == "add_reminder":
            msg = A.add_reminder(
                action.get("message", ""),
                action.get("when", ""),
                self.log
            )

        elif act == "list_reminders":
            msg = A.list_reminders(self.log)

        elif act == "clear_reminders":
            msg = A.clear_reminders(self.log)

        # ── YouTube Music ─────────────────────────────────────────────
        elif act == "play_youtube":
            msg = A.play_youtube(action.get("query", ""), self.log)

        elif act == "stop_music":
            msg = A.stop_music(self.log)

        # ── Currency ──────────────────────────────────────────────────
        elif act == "convert_currency":
            msg = A.convert_currency(
                float(action.get("amount", 1)),
                action.get("from_cur", "USD"),
                action.get("to_cur", "RUB"),
                self.log
            )

        # ── File Search ───────────────────────────────────────────────
        elif act == "find_file":
            msg = A.find_file(action.get("name", ""), self.log)

        # ── GPU Stats ──────────────────────────────────────────────────
        elif act == "gpu_stats":
            msg = A.get_gpu_stats(self.log)

        # ── Window Management ─────────────────────────────────────────
        elif act == "maximize_window":
            msg = A.maximize_window(self.log)

        elif act == "minimize_window":
            msg = A.minimize_window(self.log)

        elif act == "switch_window":
            msg = A.switch_window(self.log)

        # ── News ───────────────────────────────────────────────────────
        elif act == "get_news":
            msg = A.get_news(action.get("topic", ""), self.log)

        # ── File Management ───────────────────────────────────────────
        elif act == "list_files":
            msg = A.list_files(action.get("path", "."), self.log)

        elif act == "delete_file":
            msg = A.delete_file(action.get("path", ""), self.log)

        elif act == "create_folder":
            msg = A.create_folder(action.get("path", ""), self.log)

        elif act == "copy_file":
            msg = A.copy_file(action.get("src", ""), action.get("dst", ""), self.log)

        # ── Power Timers ───────────────────────────────────────────────
        elif act == "schedule_shutdown":
            msg = A.schedule_shutdown(int(action.get("seconds", 60)), self.log)

        elif act == "cancel_shutdown":
            msg = A.cancel_shutdown(self.log)

        elif act == "shutdown_status":
            msg = A.get_shutdown_status(self.log)

        # ── Scenarios ────────────────────────────────────────────────
        elif act == "create_scenario":
            msg = A.create_scenario(action.get("name", ""), action.get("actions", []), self.log)

        elif act == "run_scenario":
            msg = A.run_scenario(action.get("name", ""), self.log)

        elif act == "list_scenarios":
            msg = A.list_scenarios(self.log)

        # ── System Info ──────────────────────────────────────────────
        elif act == "system_info":
            msg = A.get_system_info(self.log)

        elif act == "network_info":
            msg = A.get_network_info(self.log)

        # ── Wi-Fi ──────────────────────────────────────────────────────
        elif act == "list_wifi":
            msg = A.list_wifi_networks(self.log)

        elif act == "connect_wifi":
            msg = A.connect_wifi(action.get("ssid", ""), action.get("password", ""), self.log)

        elif act == "disconnect_wifi":
            msg = A.disconnect_wifi(self.log)

        elif act == "wifi_status":
            msg = A.get_wifi_status(self.log)

        # ── Screen Recording ───────────────────────────────────────────
        elif act == "start_recording":
            msg = A.start_screen_recording(self.log)

        elif act == "stop_recording":
            msg = A.stop_screen_recording(self.log)

        # ── File Compression ────────────────────────────────────────────
        elif act == "compress":
            msg = A.compress_files(action.get("files", []), action.get("output", "archive.zip"), self.log)

        elif act == "extract":
            msg = A.extract_archive(action.get("archive", ""), action.get("dest", "."), self.log)

        # ── Search in Files ────────────────────────────────────────────
        elif act == "search_in_files":
            msg = A.search_in_files(action.get("query", ""), action.get("path", "."), self.log)

        # ── Camera ────────────────────────────────────────────────────
        elif act == "take_photo":
            msg = A.take_photo(self.log)

        # ── Calendar ──────────────────────────────────────────────────
        elif act == "calendar_events":
            msg = A.get_calendar_events(self.log)

        elif act == "create_event":
            msg = A.create_calendar_event(action.get("subject", ""), action.get("start", ""), self.log)

        # ── Bluetooth ───────────────────────────────────────────────
        elif act == "list_bluetooth":
            msg = A.list_bluetooth_devices(self.log)

        elif act == "enable_bluetooth":
            msg = A.enable_bluetooth(self.log)

        elif act == "disable_bluetooth":
            msg = A.disable_bluetooth(self.log)

        # ── Display ─────────────────────────────────────────────────
        elif act == "extend_display":
            msg = A.extend_display(self.log)

        elif act == "duplicate_display":
            msg = A.duplicate_display(self.log)

        elif act == "set_primary_display":
            msg = A.set_primary_display(self.log)

        # ── Keyboard ────────────────────────────────────────────────
        elif act == "type_text":
            msg = A.type_text(action.get("text", ""), self.log)

        elif act == "press_key":
            msg = A.press_key(action.get("key", ""), self.log)

        # ── OCR ───────────────────────────────────────────────────
        elif act == "ocr_screenshot":
            msg = A.ocr_screenshot(self.log)

        # ── File Operations ─────────────────────────────────────────
        elif act == "move_file":
            msg = A.move_file(action.get("src", ""), action.get("dst", ""), self.log)

        elif act == "rename_file":
            msg = A.rename_file(action.get("old", ""), action.get("new", ""), self.log)

        # ── Services ───────────────────────────────────────────────
        elif act == "list_services":
            msg = A.list_services(self.log)

        elif act == "start_service":
            msg = A.start_service(action.get("name", ""), self.log)

        elif act == "stop_service":
            msg = A.stop_service(action.get("name", ""), self.log)

        # ── Disk Cleanup ────────────────────────────────────────────
        elif act == "clean_temp":
            msg = A.clean_temp_files(self.log)

        elif act == "empty_recycle_full":
            msg = A.empty_recycle_bin_full(self.log)

        # ── Power Modes ────────────────────────────────────────────
        elif act == "sleep_mode":
            msg = A.sleep_mode(self.log)

        elif act == "hibernate_mode":
            msg = A.hibernate_mode(self.log)

        # ── Audio Devices ──────────────────────────────────────────
        elif act == "list_audio_devices":
            msg = A.list_audio_devices(self.log)

        elif act == "none":
            return

        else:
            self.log.warn("РОУТЕР", f"Неизвестная команда: {act}")
            msg = f"Сэр, команда «{act}» не поддерживается."
            tts.speak(msg)
            return

        if msg:
            tts.speak(msg)
