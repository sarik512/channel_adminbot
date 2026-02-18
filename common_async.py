"""
Общие функции и переменные для асинхронного бота
Используется всеми модулями обработчиков
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Support multiple super admins split by comma
raw_super_admins = os.getenv("SUPER_ADMIN_ID", "0")
SUPER_ADMIN_IDS = [int(x.strip()) for x in raw_super_admins.split(",") if x.strip()]

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))


def is_super_admin(user_id: int) -> bool:
    """Проверка супер-админа"""
    return user_id in SUPER_ADMIN_IDS


def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
