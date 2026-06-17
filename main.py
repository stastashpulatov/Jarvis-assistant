"""J.A.R.V.I.S. — точка входа"""
import os
import sys

# Убеждаемся что запуск из папки проекта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from core.assistant import Assistant


def main():
    assistant = Assistant(config_path="config.yaml")
    assistant.run()


if __name__ == "__main__":
    main()
