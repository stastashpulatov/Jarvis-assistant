"""
Характер и реплики JARVIS в духе «Железного человека».
"""
import random
import datetime
import time


ACTIVATION_LINES = [
    "Да, сэр?",
    "Слушаю вас, сэр.",
    "К вашим услугам, сэр.",
    "Все системы готовы, сэр. Чем могу помочь?",
    "JARVIS на связи, сэр.",
    "Готов к работе, сэр.",
    "Система готова, сэр.",
    "Жду указаний, сэр.",
    "Слушаю, сэр.",
]

STANDBY_LINES = [
    "Перехожу в режим ожидания, сэр. Обращайтесь.",
    "Системы в спящем режиме. Я на связи, сэр.",
    "До связи, сэр.",
    "В режиме ожидания, сэр.",
    "Мониторинг активен, сэр.",
]

BOOT_SUBSYSTEMS = [
    ("Ядро JARVIS",          0.08),
    ("Аудиоинтерфейс",       0.06),
    ("Распознавание речи",   0.10),
    ("Синтез речи",          0.07),
    ("Маршрутизатор команд", 0.05),
    ("Протоколы безопасности", 0.06),
    ("Нейросеть Gemini",     0.09),
]

IDENTITY_LINES = [
    "Я J.A.R.V.I.S. — Just A Rather Very Intelligent System, сэр. "
    "Ваш персональный интеллект для управления системой.",
    "JARVIS, сэр. Just A Rather Very Intelligent System. "
    "Полностью функционален и к вашим услугам.",
]

WITTY_OK = [
    "Выполняю, сэр.",
    "Сделано, сэр.",
    "Как прикажете, сэр.",
    "Уже занимаюсь, сэр.",
]

PROACTIVE_SUGGESTIONS = [
    "Сэр, рекомендую сделать короткий перерыв: встать, размять плечи и дать глазам десять минут отдыха.",
    "Сэр, могу запустить рабочий режим, проверить систему или найти нужную информацию. Чем займёмся?",
    "Сэр, стоит выпить воды и на минуту отвлечься от экрана. Производительность иногда любит заботу.",
    "Сэр, могу провести диагностику, проверить заряд батареи или показать текущее время.",
    "Сэр, если вы работаете давно, предлагаю перерыв. Десять минут тишины могут спасти следующий час.",
]

QUICK_HELP_LINES = [
    "Сэр, могу открыть приложения и сайты, найти информацию, управлять громкостью, проверить погоду, батарею, систему и сделать скриншот.",
    "Я могу включить рабочий, игровой, ночной или презентационный режим, сэр. Также доступна диагностика системы.",
    "Сэр, скажите: «открой браузер», «поставь звук на 60», «погода», «диагностика» или «рабочий режим».",
]


def time_greeting() -> str:
    h = datetime.datetime.now().hour
    if 5 <= h < 12:
        return "Доброе утро, сэр."
    if 12 <= h < 18:
        return "Добрый день, сэр."
    if 18 <= h < 23:
        return "Добрый вечер, сэр."
    return "Доброй ночи, сэр."


def boot_speech(user_name: str = "сэр") -> str:
    greet = time_greeting()
    return (
        f"{greet} JARVIS онлайн. "
        f"Все системы работают в штатном режиме, {user_name}. "
        f"Ожидаю кодовое слово."
    )


def activation_line() -> str:
    return random.choice(ACTIVATION_LINES)


def standby_line() -> str:
    return random.choice(STANDBY_LINES)


def proactive_line() -> str:
    return random.choice(PROACTIVE_SUGGESTIONS)


def quick_help_line() -> str:
    return random.choice(QUICK_HELP_LINES)


def identity_line() -> str:
    return random.choice(IDENTITY_LINES)


def print_boot_sequence(log_fn=None):
    """HUD-загрузка в консоли — как в фильме."""
    cyan, green, dim, reset = "\033[96m", "\033[92m", "\033[2m", "\033[0m"
    print(f"\n  {cyan}[ СИСТЕМА ]{reset} Инициализация J.A.R.V.I.S.\n")
    for name, delay in BOOT_SUBSYSTEMS:
        time.sleep(delay)
        print(f"  {dim}[BOOT]{reset}  {name:<28} {green}OK{reset}")
        if log_fn:
            log_fn("BOOT", f"{name} — OK")
    print(f"\n  {cyan}[ СИСТЕМА ]{reset} Загрузка завершена.\n")


def hud_status(active: bool, wakeword: str):
    """Строка статуса HUD."""
    cyan, yellow, dim, reset = "\033[96m", "\033[93m", "\033[2m", "\033[0m"
    mode = f"{yellow}АКТИВЕН{reset}" if active else f"{dim}ОЖИДАНИЕ{reset}"
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"  {dim}{ts}{reset}  {cyan}| JARVIS |{reset}  {mode}  "
          f"{dim}| «{wakeword}»{reset}\n")
