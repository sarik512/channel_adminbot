from typing import Tuple


def parse_title_input(text: str) -> Tuple:
    """Парсит строку вида: "Название Сезон Серия" или "Название Сезон Серия1-Серия2".

    Правила:
    - Последние два токена должны быть числа (season, episode) или (season, episode_range)
    - Всё, что до них — название (строка)
    - Поддерживает диапазон серий: "1-12" означает серии с 1 по 12

    Returns:
    - Если одна серия: (title, season, episode)
    - Если диапазон: (title, season, episode_start, episode_end)

    Raises ValueError on invalid format.
    """
    if not text or not text.strip():
        raise ValueError("Empty input")

    parts = text.strip().split()
    if len(parts) < 3:
        raise ValueError("Expected at least 3 tokens: title season episode")

    try:
        season = int(parts[-2])
        episode_part = parts[-1]
        
        # Проверяем, есть ли диапазон (например, "1-12")
        if '-' in episode_part:
            episode_parts = episode_part.split('-')
            if len(episode_parts) != 2:
                raise ValueError("Invalid episode range format")
            
            episode_start = int(episode_parts[0])
            episode_end = int(episode_parts[1])
            
            if episode_start >= episode_end:
                raise ValueError("Episode start must be less than episode end")
            
            title = " ".join(parts[:-2]).strip()
            if not title:
                raise ValueError("Title cannot be empty")
            
            return title, season, episode_start, episode_end
        else:
            # Одна серия
            episode = int(episode_part)
            
            title = " ".join(parts[:-2]).strip()
            if not title:
                raise ValueError("Title cannot be empty")
            
            return title, season, episode
            
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("Season and episode must be integers or range (e.g., 1-12)")
        raise


def generate_tag(title: str) -> str:
    """Генерирует тег из названия: заменяет пробелы на '_' и добавляет префикс '#'.

    Простая реализация: удаляет лишние пробелы и заменяет пробелы на подчёркивания.
    """
    if not title:
        return "#"
    norm = "_".join(title.strip().split())
    return f"#{norm}"


def parse_channel_id(text: str) -> str:
    """Парсит ID канала из различных форматов.
    
    Поддерживаемые форматы:
    - @channel_username
    - https://t.me/channel_username
    - t.me/channel_username
    - -1001234567890 (числовой ID)
    - https://t.me/+XaaureBEZzMwNDk6 (приватная ссылка - вернет как есть для проверки)
    
    Returns:
        str: ID канала в формате @username или -100... или None для приватных ссылок
        
    Raises:
        ValueError: если формат не распознан
    """
    if not text or not text.strip():
        raise ValueError("Empty input")
    
    text = text.strip()
    
    # Если это числовой ID (приватный канал)
    if text.startswith('-100'):
        return text
    
    # Если уже в формате @username
    if text.startswith('@'):
        return text
    
    # Если это URL
    if 't.me/' in text or 'telegram.me/' in text:
        # Проверяем, это приватная ссылка-приглашение
        if '/+' in text or 't.me/+' in text:
            # Это приватная ссылка-приглашение
            # Для таких каналов нужен числовой ID, который можно получить только после вступления
            # Возвращаем None, чтобы показать специальное сообщение
            return None
        
        # Извлекаем username из URL
        # Поддерживаемые форматы:
        # https://t.me/channel_username
        # http://t.me/channel_username
        # t.me/channel_username
        # telegram.me/channel_username
        
        # Убираем протокол
        if text.startswith('https://'):
            text = text[8:]
        elif text.startswith('http://'):
            text = text[7:]
        
        # Убираем домен
        if text.startswith('t.me/'):
            username = text[5:]
        elif text.startswith('telegram.me/'):
            username = text[12:]
        else:
            raise ValueError("Invalid URL format")
        
        # Убираем возможные параметры и слэши
        username = username.split('?')[0].split('/')[0].strip()
        
        if not username:
            raise ValueError("Username not found in URL")
        
        # Добавляем @
        return f"@{username}"
    
    # Если это просто username без @
    if text and not text.startswith('@') and not text.startswith('-'):
        return f"@{text}"
    
    raise ValueError("Invalid channel ID format")
