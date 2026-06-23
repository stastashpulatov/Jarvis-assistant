"""Системный трей и уведомления JARVIS."""
import threading
import pystray
from PIL import Image, ImageDraw, ImageFont
from plyer import notification
from typing import Callable


class TrayIcon:
    """Иконка в системном трее с контекстным меню."""
    
    def __init__(self, on_activate: Callable = None, on_quit: Callable = None):
        self.on_activate = on_activate
        self.on_quit = on_quit
        self.icon = None
        self._running = False
    
    def _create_icon_image(self) -> Image.Image:
        """Создаёт иконку JARVIS."""
        # Создаём синий круг с буквой J
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Синий круг
        draw.ellipse([4, 4, size-4, size-4], fill=(0, 100, 200, 255))
        
        # Буква J
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((18, 8), "J", fill=(255, 255, 255, 255), font=font)
        
        return image
    
    def _toggle_active(self, icon, item):
        """Переключает активность."""
        if self.on_activate:
            self.on_activate()
    
    def _quit(self, icon, item):
        """Выход."""
        self._running = False
        icon.stop()
        if self.on_quit:
            self.on_quit()
    
    def show_notification(self, title: str, message: str):
        """Показывает уведомление Windows."""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="JARVIS",
                timeout=5
            )
        except Exception as e:
            print(f"[ТРЕЙ] Ошибка уведомления: {e}")
    
    def run(self, active: bool = True):
        """Запускает иконку в отдельном потоке."""
        if self._running:
            return
        
        self._running = True
        
        menu = pystray.Menu(
            pystray.MenuItem("Активен" if active else "Пауза", self._toggle_active),
            pystray.MenuItem("Выход", self._quit)
        )
        
        self.icon = pystray.Icon(
            "JARVIS",
            self._create_icon_image(),
            menu=menu
        )
        
        def run_icon():
            self.icon.run()
        
        threading.Thread(target=run_icon, daemon=True).start()
    
    def stop(self):
        """Останавливает иконку."""
        if self.icon:
            self._running = False
            self.icon.stop()
