"""Тесты для локального парсера."""
import pytest
from core.local_parser import try_parse


class TestLocalParser:
    """Тесты локального парсера команд."""
    
    def test_open_app(self):
        """Тест открытия приложений."""
        speech, actions = try_parse("открой хром")
        assert len(actions) == 1
        assert actions[0]["action"] == "open_app"
        assert "chrome" in actions[0]["target"].lower()
    
    def test_volume_set(self):
        """Тест установки громкости."""
        speech, actions = try_parse("поставь звук на 50")
        assert len(actions) == 1
        assert actions[0]["action"] == "volume_set"
        assert actions[0]["level"] == 50
    
    def test_volume_up(self):
        """Тест увеличения громкости."""
        speech, actions = try_parse("громче")
        assert len(actions) == 1
        assert actions[0]["action"] == "volume_up"
    
    def test_volume_down(self):
        """Тест уменьшения громкости."""
        speech, actions = try_parse("тише")
        assert len(actions) == 1
        assert actions[0]["action"] == "volume_down"
    
    def test_show_time(self):
        """Тест показа времени."""
        speech, actions = try_parse("сколько время")
        assert len(actions) == 1
        assert actions[0]["action"] == "show_time"
    
    def test_show_date(self):
        """Тест показа даты."""
        speech, actions = try_parse("какая дата")
        assert len(actions) == 1
        assert actions[0]["action"] == "show_date"
    
    def test_weather(self):
        """Тест погоды."""
        speech, actions = try_parse("погода в москве")
        assert len(actions) == 1
        assert actions[0]["action"] == "weather"
        assert "moscow" in actions[0]["city"].lower()
    
    def test_search(self):
        """Тест поиска."""
        speech, actions = try_parse("найди python tutorial")
        assert len(actions) == 1
        assert actions[0]["action"] == "search"
        assert "python" in actions[0]["query"].lower()
    
    def test_lock(self):
        """Тест блокировки."""
        speech, actions = try_parse("заблокируй")
        assert len(actions) == 1
        assert actions[0]["action"] == "lock"
    
    def test_shutdown(self):
        """Тест выключения."""
        speech, actions = try_parse("выключи")
        assert len(actions) == 1
        assert actions[0]["action"] == "shutdown"
    
    def test_quick_yes(self):
        """Тест быстрого ответа да."""
        speech, actions = try_parse("да")
        assert speech is not None
        assert len(actions) == 0
    
    def test_quick_no(self):
        """Тест быстрого ответа нет."""
        speech, actions = try_parse("нет")
        assert speech is not None
        assert len(actions) == 0
    
    def test_quick_thanks(self):
        """Тест благодарности."""
        speech, actions = try_parse("спасибо")
        assert speech is not None
        assert len(actions) == 0
    
    def test_compound_command(self):
        """Тест составной команды."""
        speech, actions = try_parse("открой хром и блокнот")
        assert len(actions) == 2
        assert actions[0]["action"] == "open_app"
        assert actions[1]["action"] == "open_app"
    
    def test_unknown_command(self):
        """Тест неизвестной команды."""
        result = try_parse("абракадабра")
        assert result is None  # Должен идти в AI


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
