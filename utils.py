from typing import Tuple


def parse_title_input(text: str) -> Tuple[str, int, int]:
    """Парсит строку вида: "Название Сезон Серия".

    Правила:
    - Последние два токена должны быть числа (season, episode)
    - Всё, что до них — название (строка)

    Raises ValueError on invalid format.
    """
    if not text or not text.strip():
        raise ValueError("Empty input")

    parts = text.strip().split()
    if len(parts) < 3:
        raise ValueError("Expected at least 3 tokens: title season episode")

    try:
        season = int(parts[-2])
        episode = int(parts[-1])
    except ValueError:
        raise ValueError("Season and episode must be integers")

    title = " ".join(parts[:-2]).strip()
    if not title:
        raise ValueError("Title cannot be empty")

    return title, season, episode


def generate_tag(title: str) -> str:
    """Генерирует тег из названия: заменяет пробелы на '_' и добавляет префикс '#'.

    Простая реализация: удаляет лишние пробелы и заменяет пробелы на подчёркивания.
    """
    if not title:
        return "#"
    norm = "_".join(title.strip().split())
    return f"#{norm}"
