"""
Общие функции и переменные для асинхронного бота
Используется всеми модулями обработчиков
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", 0))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))


def is_super_admin(user_id: int) -> bool:
    """Проверка супер-админа"""
    return user_id == SUPER_ADMIN_ID


def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
