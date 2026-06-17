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

        elif act == "none":
            return

        else:
            self.log.warn("РОУТЕР", f"Неизвестная команда: {act}")
            msg = f"Сэр, команда «{act}» не поддерживается."
            tts.speak(msg)
            return

        if msg:
            tts.speak(msg)
