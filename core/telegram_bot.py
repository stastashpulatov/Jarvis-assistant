"""Telegram-бот для управления JARVIS."""
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Callable


class TelegramBot:
    """Telegram-бот как дополнительный интерфейс."""
    
    def __init__(self, token: str, process_callback: Callable):
        self.token = token
        self.process_callback = process_callback
        self.application = None
        self._running = False
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовые сообщения."""
        if update.message and update.message.text:
            user_text = update.message.text
            try:
                # Используем тот же процессор что и голосовой режим
                speech, actions = self.process_callback(user_text)
                
                if speech:
                    await update.message.reply_text(speech)
                else:
                    await update.message.reply_text("Команда выполнена, сэр.")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {e}")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /start."""
        await update.message.reply_text(
            "J.A.R.V.I.S. онлайн, сэр.\n"
            "Отправьте команду как в голосовом режиме."
        )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /help."""
        help_text = (
            "Доступные команды:\n"
            "- открой [приложение]\n"
            "- поставь звук на [число]\n"
            "- погода в [город]\n"
            "- найди [запрос]\n"
            "- заблокируй\n"
            "- выключи\n"
            "- и многие другие..."
        )
        await update.message.reply_text(help_text)
    
    def run(self):
        """Запускает бота в отдельном потоке."""
        if not self.token or self.token in ("ВАШ_ТОКЕН", "", "YOUR_TOKEN"):
            print("[TELEGRAM] Токен не задан. Бот не запущен.")
            return
        
        if self._running:
            return
        
        self._running = True
        
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        def run_bot():
            try:
                self.application.run_polling()
            except Exception as e:
                print(f"[TELEGRAM] Ошибка: {e}")
        
        threading.Thread(target=run_bot, daemon=True).start()
        print("[TELEGRAM] Бот запущен")
    
    def stop(self):
        """Останавливает бота."""
        if self.application:
            self._running = False
            self.application.stop()
