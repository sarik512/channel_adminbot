"""
Асинхронная версия бота на aiogram 3.x
Современная архитектура с роутерами и middleware
"""
import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

import database_async as db
from utils import parse_title_input, generate_tag, parse_channel_id

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Support multiple super admins split by comma
raw_super_admins = os.getenv("SUPER_ADMIN_ID", "0")
SUPER_ADMIN_IDS = [int(x.strip()) for x in raw_super_admins.split(",") if x.strip()]

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# ================== FSM STATES ==================

class UploadStates(StatesGroup):
    """Состояния для загрузки контента"""
    waiting_info = State()
    selecting_channel = State()
    waiting_video = State()


class ChannelStates(StatesGroup):
    """Состояния для управления каналами"""
    adding_channel = State()
    adding_channel_name = State()
    confirming_channel_without_rights = State()
    deleting_channel = State()


class AdminStates(StatesGroup):
    """Состояния для управления админами"""
    adding_admin = State()
    selecting_admin = State()
    admin_actions = State()
    admin_channels = State()
    attaching_channel = State()


class TemplateStates(StatesGroup):
    """Состояния для управления шаблонами"""
    adding_template_name = State()
    adding_template_text = State()
    selecting_template = State()
    template_actions = State()
    editing_template = State()
    selecting_template_for_channel = State()
    assigning_template_to_channel = State()


# ================== HELPER FUNCTIONS ==================

def is_super_admin(user_id: int) -> bool:
    """Проверка супер-админа"""
    return user_id in SUPER_ADMIN_IDS


async def is_admin_check(user_id: int) -> bool:
    """Проверка админа (async)"""
    if is_super_admin(user_id):
        return True
    return await db.is_admin(user_id)


def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def parse_input(text: str):
    """Парсер информации о видео"""
    try:
        result = parse_title_input(text)
        
        if len(result) == 4:
            # Диапазон серий
            title, season, episode_start, episode_end = result
            tag = generate_tag(title)
            
            return {
                "title": title,
                "season": int(season),
                "episode": None,
                "episode_start": int(episode_start),
                "episode_end": int(episode_end),
                "tag": tag,
                "is_range": True
            }
        else:
            # Одна серия
            title, season, episode = result
            tag = generate_tag(title)
            
            return {
                "title": title,
                "season": int(season),
                "episode": int(episode),
                "episode_start": None,
                "episode_end": None,
                "tag": tag,
                "is_range": False
            }
    except ValueError:
        return None


# ================== KEYBOARDS ==================

def main_menu_keyboard(is_super: bool) -> ReplyKeyboardMarkup:
    """Главное меню"""
    buttons = []
    
    if is_super:
        buttons.extend([
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📺 Каналы")],
            [KeyboardButton(text="👥 Админы"), KeyboardButton(text="📝 Шаблоны")],
            [KeyboardButton(text="📤 Загрузить")]
        ])
    else:
        buttons.extend([
            [KeyboardButton(text="📤 Загрузить контент")],
            [KeyboardButton(text="📺 Мои каналы"), KeyboardButton(text="📊 Моя статистика")]
        ])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def back_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка назад"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 НАЗАД")]],
        resize_keyboard=True
    )


def back_and_home_keyboard() -> ReplyKeyboardMarkup:
    """Кнопки назад и в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="🔙 НАЗАД"),
            KeyboardButton(text="🏠 Главное меню")
        ]],
        resize_keyboard=True
    )


# ================== HANDLERS ==================

@router.message(Command("start", "menu"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    logging.info(f"📱 /start from {user_id}")
    
    # Проверка админа
    if not await is_admin_check(user_id):
        await message.answer(
            "⛔ У тебя нет доступа к этому боту.\n"
            "Свяжись с главным админом."
        )
        return
    
    # Обновляем username
    username = message.from_user.username or message.from_user.full_name
    await db.add_admin(user_id, username=username)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем главное меню
    is_super = is_super_admin(user_id)
    keyboard = main_menu_keyboard(is_super)
    
    await message.answer(
        "🎬 *Бот загрузки аниме*\n\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(F.text.in_(["🔙 НАЗАД"]))
async def btn_back(message: Message, state: FSMContext):
    """Кнопка назад"""
    user_id = message.from_user.id
    
    if not await is_admin_check(user_id):
        return
    
    await state.clear()
    
    is_super = is_super_admin(user_id)
    keyboard = main_menu_keyboard(is_super)
    
    await message.answer(
        "🔙 Возврат назад",
        reply_markup=keyboard
    )


@router.message(F.text.in_(["🏠 Главное меню", "🔙 Главное меню"]))
async def btn_home(message: Message, state: FSMContext):
    """Кнопка в главное меню"""
    user_id = message.from_user.id
    
    if not await is_admin_check(user_id):
        return
    
    await state.clear()
    
    is_super = is_super_admin(user_id)
    keyboard = main_menu_keyboard(is_super)
    
    await message.answer(
        "🎬 *Бот загрузки аниме*\n\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(F.text == "📊 Статистика")
async def btn_statistics(message: Message):
    """Показать статистику (только супер-админ)"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    stats = await db.get_all_stats()
    response = "📊 *Общая статистика*\n\n"
    
    if not stats:
        response += "❌ Нет данных"
    else:
        for s in stats:
            username = s.get('username') or f"ID: {s['user_id']}"
            username_safe = escape_markdown(username)
            total = s['total_uploads']
            response += f"• {username_safe}: *{total}* загрузок\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(F.text == "📊 Моя статистика")
async def btn_my_statistics(message: Message):
    """Показать мою статистику"""
    user_id = message.from_user.id
    
    if not await is_admin_check(user_id):
        return
    
    stats = await db.get_admin_stats(user_id)
    response = f"📊 *Моя статистика*\n\n"
    response += f"Всего загрузок: *{stats['total']}*\n\n"
    
    if stats['by_channel']:
        response += "*По каналам:*\n"
        for ch in stats['by_channel']:
            response += f"• {ch['channel_name']}: {ch['count']}\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(F.text == "📺 Мои каналы")
async def btn_my_channels(message: Message):
    """Показать мои каналы"""
    user_id = message.from_user.id
    
    if not await is_admin_check(user_id):
        return
    
    channels = await db.get_admin_channels(user_id)
    response = "📺 *Мои каналы*\n\n"
    
    if not channels:
        response += "❌ Вы не назначены ни на один канал\n\n"
        response += "ℹ️ Обратитесь к главному администратору для получения доступа к каналам."
    else:
        for ch in channels:
            response += f"• {ch['channel_name']}\n"
    
    await message.answer(response, parse_mode="Markdown")


# ================== MAIN ==================

async def main():
    """Главная функция запуска бота"""
    # Инициализация БД
    await db.init_db()
    logging.info("✅ База данных инициализирована")
    
    # Ensure super admins are in DB
    for admin_id in SUPER_ADMIN_IDS:
        if not await db.is_admin(admin_id):
            await db.add_admin(admin_id, username="Super Admin")
            logging.info(f"SUPER_ADMIN {admin_id} added to database")
    
    # Импортируем и регистрируем все роутеры
    from handlers_upload import router as upload_router
    from handlers_channels import router as channels_router
    from handlers_admins import router as admins_router
    from handlers_templates import router as templates_router
    
    # Регистрация роутеров (порядок важен!)
    dp.include_router(router)  # Основной роутер
    dp.include_router(upload_router)  # Загрузка контента
    dp.include_router(channels_router)  # Управление каналами
    dp.include_router(admins_router)  # Управление админами
    dp.include_router(templates_router)  # Управление шаблонами
    
    # Запуск бота
    logging.info("🤖 Асинхронный бот запускается...")
    print("✅ Асинхронный бот запущен и готов к работе!")
    print("📊 Все модули загружены:")
    print("  ✅ Основные обработчики")
    print("  ✅ Загрузка контента")
    print("  ✅ Управление каналами")
    print("  ✅ Управление админами")
    print("  ✅ Управление шаблонами")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
