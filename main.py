import os
import logging
import telebot
from telebot import types
from dotenv import load_dotenv
import database as db
import keyboards as kb
import time
import socket

# ================== ENV ==================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID"))
# Максимальный размер файла в байтах (по умолчанию 100 MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024

# ================== LOGGING ==================
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

logging.info("🚀 Bot starting...")

# ================== BOT ==================
bot = telebot.TeleBot(BOT_TOKEN)

ADMINS_FILE = "admins.json"
user_data = {}

# ================== DATABASE INIT ==================
db.init_db()
db.migrate_from_json(ADMINS_FILE)

# Ensure super admin is in DB
if not db.is_admin(SUPER_ADMIN_ID):
    db.add_admin(SUPER_ADMIN_ID, username="Super Admin")
    logging.info("SUPER_ADMIN added to database")

# ================== HELPER FUNCTIONS ==================
def is_admin(user_id):
    """Проверка, является ли пользователь админом"""
    if user_id == SUPER_ADMIN_ID:
        logging.info(f"Admin check | user={user_id} | SUPER_ADMIN=True")
        return True
    
    result = db.is_admin(user_id)
    logging.info(f"Admin check | user={user_id} | result={result}")
    return result

def is_super_admin(user_id):
    """Проверка, является ли пользователь супер-админом"""
    return user_id == SUPER_ADMIN_ID

def get_user_state(user_id):
    """Получить состояние пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            'state': None,
            'data': {},
            'channel_id': None,
            'temp': {}
        }
    return user_data[user_id]

def clear_user_state(user_id):
    """Очистить состояние пользователя"""
    if user_id in user_data:
        del user_data[user_id]


def escape_markdown(text: str) -> str:
    """Экранировать специальные символы Markdown"""
    if not text:
        return text
    # Экранируем символы, которые имеют специальное значение в Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def send_super_admin_alert(text: str):
    """Попытка оповестить главного админа в случае критической ошибки/восстановления"""
    try:
        bot.send_message(SUPER_ADMIN_ID, text)
    except Exception as e:
        logging.error(f"Failed to notify super admin: {e}")


def can_resolve_api() -> bool:
    """Проверка DNS для api.telegram.org"""
    try:
        socket.gethostbyname('api.telegram.org')
        return True
    except Exception:
        return False

# ================== PARSER ==================
from utils import parse_title_input, generate_tag, parse_channel_id


def parse_input(text):
    """Парсер ожиданий: "Название Сезон Серия" или "Название Сезон Серия1-Серия2"
    
    Возвращает dict с:
    - title: название
    - season: сезон (int)
    - episode: серия (int) или None если диапазон
    - episode_start: начало диапазона (int) или None
    - episode_end: конец диапазона (int) или None
    - tag: тег
    - is_range: True если диапазон серий
    """
    try:
        result = parse_title_input(text)
        
        # Проверяем, вернулся ли диапазон или одна серия
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

# ================== HANDLERS ==================
@bot.message_handler(commands=['start', 'menu'])
def start(message):
    user_id = message.from_user.id
    logging.info(f"📱 /start from {user_id}")
    print(f"📱 /start from {user_id}")  # Для консоли

    if not is_admin(user_id):
        bot.reply_to(
            message,
            "⛔ У тебя нет доступа к этому боту.\n"
            "Свяжись с главным админом."
        )
        logging.warning(f"Access denied for {user_id}")
        return

    # Очистить состояние при возврате в меню
    clear_user_state(user_id)
    
    is_super = is_super_admin(user_id)
    logging.info(f"Creating menu for user {user_id}, is_super_admin={is_super}")
    print(f"Creating menu: is_super_admin={is_super}")
    
    # Используем Reply клавиатуру вместо inline
    markup = kb.main_menu_reply(is_super)
    logging.info(f"Reply markup created")
    print(f"Reply markup created")
    
    bot.send_message(
        message.chat.id,
        "🎬 *Бот загрузки аниме*\n\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    logging.info(f"Menu sent to {user_id}")
    print(f"✅ Menu sent to {user_id}")



# ================== CALLBACK HANDLERS ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Главный обработчик всех нажатий на кнопки"""
    user_id = call.from_user.id
    data = call.data
    
    logging.info(f"🔘 CALLBACK RECEIVED | user={user_id} | data={data}")
    print(f"🔘 CALLBACK: {data} from {user_id}")  # Для консоли
    
    if not is_admin(user_id):
        logging.warning(f"⛔ Access denied for callback | user={user_id}")
        bot.answer_callback_query(call.id, "⛔ Нет доступа")
        return
    
    try:
        # ========== MENU NAVIGATION ==========
        if data == "menu:main":
            clear_user_state(user_id)  # Очистить состояние при возврате в главное меню
            markup = kb.main_menu(is_super_admin(user_id))
            try:
                bot.edit_message_text(
                    "🎬 *Бот загрузки аниме*\n\nВыберите действие:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                # Если не удалось отредактировать, отправим новое сообщение
                logging.warning(f"Failed to edit message: {e}")
                bot.send_message(
                    call.message.chat.id,
                    "🎬 *Бот загрузки аниме*\n\nВыберите действие:",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
        
        elif data == "menu:channels":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            markup = kb.channels_menu()
            bot.edit_message_text(
                "📺 *Управление каналами*",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "menu:admins":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            markup = kb.admins_menu()
            bot.edit_message_text(
                "👥 *Управление админами*",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        # ========== CHANNELS ==========
        elif data == "channel:add":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            
            state = get_user_state(user_id)
            state['state'] = 'adding_channel'
            
            markup = kb.cancel_keyboard()
            bot.edit_message_text(
                "📺 *Добавление канала*\n\n"
                "Отправьте ID канала (например: @channel или -1001234567890):",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "channel:list":
            channels = db.get_all_channels()
            if not channels:
                text = "📺 *Список каналов*\n\n❌ Нет добавленных каналов"
                markup = kb.back_button("menu:channels")
            else:
                text = "📺 *Список каналов*\n\n"
                for ch in channels:
                    text += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
                markup = kb.back_button("menu:channels")
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        # ========== ADMINS ==========
        elif data == "admin:add":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            
            state = get_user_state(user_id)
            state['state'] = 'adding_admin'
            
            markup = kb.cancel_keyboard()
            bot.edit_message_text(
                "👤 *Добавление админа*\n\n"
                "Отправьте Telegram ID пользователя:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "admin:list":
            admins = db.get_all_admins()
            text = "👥 *Список админов*\n\n"
            for admin in admins:
                username = admin.get('username') or f"ID: {admin['user_id']}"
                is_super = " 👑" if admin['user_id'] == SUPER_ADMIN_ID else ""
                text += f"• {username}{is_super}\n"
            
            markup = kb.back_button("menu:admins")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "admin:assign_menu":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            
            admins = db.get_all_admins()
            markup = kb.admin_list_keyboard(admins, action="assign")
            bot.edit_message_text(
                "🔗 *Назначение админов*\n\nВыберите админа:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data.startswith("admin:assign:"):
            admin_id = int(data.split(":")[2])
            all_channels = db.get_all_channels()
            assigned = db.get_admin_channels(admin_id)
            
            admin_info = db.get_admin(admin_id)
            username = admin_info.get('username') or f"ID: {admin_id}"
            
            markup = kb.assign_channels_keyboard(admin_id, all_channels, assigned)
            bot.edit_message_text(
                f"🔗 *Назначение каналов для {username}*\n\n"
                "Нажмите на канал чтобы назначить/убрать:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data.startswith("assign:"):
            parts = data.split(":")
            admin_id = int(parts[1])
            channel_id = parts[2]
            
            db.assign_admin_to_channel(admin_id, channel_id)
            bot.answer_callback_query(call.id, "✅ Назначен")
            
            # Refresh keyboard
            all_channels = db.get_all_channels()
            assigned = db.get_admin_channels(admin_id)
            admin_info = db.get_admin(admin_id)
            username = admin_info.get('username') or f"ID: {admin_id}"
            
            markup = kb.assign_channels_keyboard(admin_id, all_channels, assigned)
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        
        elif data.startswith("unassign:"):
            parts = data.split(":")
            admin_id = int(parts[1])
            channel_id = parts[2]
            
            db.unassign_admin_from_channel(admin_id, channel_id)
            bot.answer_callback_query(call.id, "✅ Убран")
            
            # Refresh keyboard
            all_channels = db.get_all_channels()
            assigned = db.get_admin_channels(admin_id)
            
            markup = kb.assign_channels_keyboard(admin_id, all_channels, assigned)
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        
        # ========== STATISTICS ==========
        elif data == "stats:all":
            if not is_super_admin(user_id):
                bot.answer_callback_query(call.id, "⛔ Только для супер-админа")
                return
            
            stats = db.get_all_stats()
            text = "📊 *Общая статистика*\n\n"
            
            if not stats:
                text += "❌ Нет данных"
            else:
                for s in stats:
                    username = s.get('username') or f"ID: {s['user_id']}"
                    total = s['total_uploads']
                    text += f"• {username}: *{total}* загрузок\n"
            
            markup = kb.back_button("menu:main")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "stats:my":
            stats = db.get_admin_stats(user_id)
            text = f"📊 *Моя статистика*\n\n"
            text += f"Всего загрузок: *{stats['total']}*\n\n"
            
            if stats['by_channel']:
                text += "*По каналам:*\n"
                for ch in stats['by_channel']:
                    text += f"• {ch['channel_name']}: {ch['count']}\n"
            
            markup = kb.back_button("menu:main")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data == "my:channels":
            channels = db.get_admin_channels(user_id)
            text = "📺 *Мои каналы*\n\n"
            
            if not channels:
                text += "❌ Вы не назначены ни на один канал"
            else:
                for ch in channels:
                    text += f"• {ch['channel_name']}\n"
            
            markup = kb.back_button("menu:main")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        # ========== UPLOAD ==========
        elif data == "upload:start":
            channels = db.get_admin_channels(user_id) if not is_super_admin(user_id) else db.get_all_channels()
            
            if not channels:
                bot.answer_callback_query(call.id, "❌ Нет доступных каналов")
                return
            
            state = get_user_state(user_id)
            state['state'] = 'waiting_info'
            
            markup = kb.cancel_keyboard()
            bot.edit_message_text(
                "📤 *Загрузка контента*\n\n"
                "Отправьте информацию в формате:\n"
                "`Название Сезон Серия`\n\n"
                "Пример:\n"
                "`Боевой континет 1 12`",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        elif data.startswith("channel:select:"):
            channel_id = data.split(":")[2]
            state = get_user_state(user_id)
            state['channel_id'] = channel_id
            state['state'] = 'waiting_video'  # ✅ ИСПРАВЛЕНО: обновляем состояние
            
            channel = db.get_channel(channel_id)
            bot.answer_callback_query(call.id, f"✅ Выбран: {channel['channel_name']}")
            
            bot.edit_message_text(
                f"✅ Канал выбран: *{channel['channel_name']}*\n\n"
                "Теперь отправьте видео или документ.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif data == "noop":
            bot.answer_callback_query(call.id)
        
        else:
            bot.answer_callback_query(call.id, "⚠️ Неизвестная команда")
    
    except Exception as e:
        logging.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка")



# ================== TEXT MESSAGE HANDLERS ==================
@bot.message_handler(func=lambda m: bool(m.text))
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    logging.info(f"Text from {user_id}: {text}")

    if not is_admin(user_id):
        return
    
    # Обновляем username админа при каждом сообщении
    try:
        username = message.from_user.username
        if not username:
            first_name = message.from_user.first_name or ""
            last_name = message.from_user.last_name or ""
            username = f"{first_name} {last_name}".strip() or None
        
        if username:
            db.add_admin(user_id, username=username)  # Обновит существующего
    except Exception as e:
        logging.warning(f"Could not update username for {user_id}: {e}")
    
    # ========== ОБРАБОТКА REPLY КНОПОК МЕНЮ ==========
    if text == "🔙 НАЗАД":
        # Возврат на предыдущий уровень (очистка состояния)
        clear_user_state(user_id)
        is_super = is_super_admin(user_id)
        markup = kb.main_menu_reply(is_super)
        bot.send_message(
            message.chat.id,
            "🔙 Возврат назад",
            reply_markup=markup
        )
        return
    
    elif text in ["🏠 Главное меню", "🔙 Главное меню"]:
        # Возврат в главное меню (поддержка старой и новой кнопки)
        clear_user_state(user_id)
        is_super = is_super_admin(user_id)
        markup = kb.main_menu_reply(is_super)
        bot.send_message(
            message.chat.id,
            "🎬 *Бот загрузки аниме*\n\n"
            "Выберите действие с помощью кнопок ниже:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
    
    elif text == "📊 Статистика":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        stats = db.get_all_stats()
        response = "📊 *Общая статистика*\n\n"
        if not stats:
            response += "❌ Нет данных"
        else:
            for s in stats:
                username = s.get('username') or f"ID: {s['user_id']}"
                username_safe = escape_markdown(username)
                total = s['total_uploads']
                response += f"• {username_safe}: *{total}* загрузок\n"
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    elif text == "📺 Каналы":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        channels = db.get_all_channels()
        if not channels:
            response = "📺 *Управление каналами*\n\n❌ Нет добавленных каналов\n\nИспользуйте кнопку ниже для добавления."
        else:
            response = "📺 *Управление каналами*\n\n*Список каналов:*\n\n"
            for ch in channels:
                response += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
        
        # Показываем меню с кнопками
        markup = kb.channels_menu_reply()
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "👥 Админы":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        admins = db.get_all_admins()
        response = "👥 *Управление админами*\n\n*Список админов:*\n\n"
        for admin in admins:
            username = admin.get('username') or f"ID: {admin['user_id']}"
            username_safe = escape_markdown(username)
            is_super = " 👑" if admin['user_id'] == SUPER_ADMIN_ID else ""
            response += f"• {username_safe}{is_super}\n"
        
        # Показываем меню с кнопками
        markup = kb.admins_menu_reply()
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text in ["📤 Загрузить", "📤 Загрузить контент"]:
        channels = db.get_admin_channels(user_id) if not is_super_admin(user_id) else db.get_all_channels()
        if not channels:
            if is_super_admin(user_id):
                bot.reply_to(
                    message, 
                    "❌ Нет доступных каналов\n\n"
                    "Сначала добавьте каналы через меню 📺 *Каналы*",
                    parse_mode="Markdown"
                )
            else:
                bot.reply_to(
                    message, 
                    "❌ У вас нет доступных каналов\n\n"
                    "ℹ️ Вы пока не прикреплены ни к одному каналу.\n"
                    "Обратитесь к главному администратору для получения доступа.",
                    parse_mode="Markdown"
                )
            return
        
        state = get_user_state(user_id)
        state['state'] = 'waiting_info'
        
        bot.reply_to(
            message,
            "📤 *Загрузка контента*\n\n"
            "Отправьте информацию в формате:\n"
            "• `Название Сезон Серия` - для одной серии\n"
            "• `Название Сезон Серия1-Серия2` - для диапазона\n\n"
            "Примеры:\n"
            "• `Боевой континет 1 12`\n"
            "• `Боевой континет 1 1-12`",
            parse_mode="Markdown",
            reply_markup=kb.back_menu_reply()
        )
        return
    
    elif text == "📺 Мои каналы":
        channels = db.get_admin_channels(user_id)
        response = "📺 *Мои каналы*\n\n"
        if not channels:
            response += "❌ Вы не назначены ни на один канал\n\n"
            response += "ℹ️ Обратитесь к главному администратору для получения доступа к каналам."
        else:
            for ch in channels:
                response += f"• {ch['channel_name']}\n"
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    elif text == "📊 Моя статистика":
        stats = db.get_admin_stats(user_id)
        response = f"📊 *Моя статистика*\n\n"
        response += f"Всего загрузок: *{stats['total']}*\n\n"
        if stats['by_channel']:
            response += "*По каналам:*\n"
            for ch in stats['by_channel']:
                response += f"• {ch['channel_name']}: {ch['count']}\n"
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    elif text == "➕ Добавить канал":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'adding_channel'
        
        bot.reply_to(
            message,
            "📺 *Добавление канала*\n\n"
            "Отправьте ID или ссылку на канал:\n\n"
            "Форматы:\n"
            "• `@channel_username` - публичный канал\n"
            "• `https://t.me/channel_username` - ссылка на публичный канал\n"
            "• `-1001234567890` - числовой ID приватного канала\n\n"
            "❗ Для приватных ссылок (с `+`) используйте числовой ID",
            parse_mode="Markdown",
            reply_markup=kb.back_menu_reply()
        )
        return
    
    elif text == "🗑 Удалить канал":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        
        channels = db.get_all_channels()
        if not channels:
            bot.reply_to(message, "❌ Нет каналов для удаления")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'deleting_channel'
        
        # Создаем клавиатуру со списком каналов
        markup = kb.channels_select_reply(channels)
        bot.send_message(
            message.chat.id,
            "🗑 *Удаление канала*\n\n"
            "⚠️ Внимание! При удалении канала:\n"
            "• Все прикрепления админов к этому каналу будут удалены\n"
            "• Статистика загрузок сохранится\n\n"
            "Выберите канал для удаления:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text.startswith("📺 ") and text != "📺 Каналы" and text != "📺 Мои каналы" and text != "📺 Каналы админа":
        # Проверяем, это удаление канала или выбор для загрузки
        state = get_user_state(user_id)
        
        if state.get('state') == 'deleting_channel':
            # Удаление канала
            if not is_super_admin(user_id):
                return
            
            channel_name = text[2:].strip()
            
            # Находим канал по имени
            channels = db.get_all_channels()
            selected_channel = None
            for ch in channels:
                if ch['channel_name'] == channel_name:
                    selected_channel = ch
                    break
            
            if not selected_channel:
                bot.reply_to(message, "❌ Канал не найден")
                return
            
            # Удаляем канал
            channel_id = selected_channel['channel_id']
            if db.remove_channel(channel_id):
                bot.send_message(
                    message.chat.id,
                    f"✅ *Канал удален!*\n\n"
                    f"Название: *{channel_name}*\n"
                    f"ID: `{channel_id}`\n\n"
                    f"Все прикрепления админов к этому каналу также удалены.",
                    parse_mode="Markdown"
                )
                logging.info(f"Channel deleted: {channel_id} - {channel_name}")
            else:
                bot.reply_to(message, "❌ Ошибка при удалении канала")
            
            clear_user_state(user_id)
            
            # Возвращаемся к меню каналов
            channels = db.get_all_channels()
            response = "📺 *Управление каналами*\n\n"
            if channels:
                response += "*Список каналов:*\n\n"
                for ch in channels:
                    response += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
            else:
                response += "❌ Нет добавленных каналов"
            
            markup = kb.channels_menu_reply()
            bot.send_message(
                message.chat.id,
                response,
                parse_mode="Markdown",
                reply_markup=markup
            )
            return
        
        elif state.get('state') == 'selecting_channel':
            # Выбор канала при загрузке видео (существующий код)
            channel_name = text[2:].strip()
            
            # Находим канал по имени
            channels = db.get_admin_channels(user_id) if not is_super_admin(user_id) else db.get_all_channels()
            selected_channel = None
            for ch in channels:
                if ch['channel_name'] == channel_name:
                    selected_channel = ch
                    break
            
            if not selected_channel:
                bot.reply_to(message, "❌ Канал не найден")
                return
            
            # Сохраняем выбранный канал
            state['channel_id'] = selected_channel['channel_id']
            state['state'] = 'waiting_video'
            
            bot.send_message(
                message.chat.id,
                f"✅ Канал выбран: *{channel_name}*\n\n"
                "Теперь отправьте видео или документ.",
                parse_mode="Markdown",
                reply_markup=kb.back_menu_reply()
            )
            return
    
    elif text.startswith("📝 ") and text != "📝 Шаблоны":
        # Выбор шаблона из списка
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        if state.get('state') not in ['selecting_template', 'selecting_template_for_channel']:
            return
        
        template_name = text[2:].strip()
        template = db.get_template_by_name(template_name)
        
        if not template:
            bot.reply_to(message, "❌ Шаблон не найден")
            return
        
        state['selected_template_id'] = template['id']
        state['selected_template_name'] = template_name
        
        if state.get('state') == 'selecting_template_for_channel':
            # Показываем список каналов
            channels = db.get_all_channels()
            if not channels:
                bot.reply_to(message, "❌ Нет каналов")
                return
            
            state['state'] = 'assigning_template_to_channel'
            
            # Находим канал, к которому уже прикреплен этот шаблон
            assigned_channel_id = None
            for ch in channels:
                ch_template = db.get_channel_template(ch['channel_id'])
                if ch_template and ch_template['id'] == template['id']:
                    assigned_channel_id = ch['channel_id']
                    break
            
            markup = kb.channels_for_template_reply(channels, assigned_channel_id)
            bot.send_message(
                message.chat.id,
                f"📺 *Прикрепление шаблона '{escape_markdown(template_name)}'*\n\n"
                "Выберите канал:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            # Показываем меню действий с шаблоном
            state['state'] = 'template_actions'
            markup = kb.template_actions_menu_reply(template_name)
            
            response = f"📝 *Шаблон: {escape_markdown(template_name)}*\n\n"
            response += f"ID: `{template['id']}`\n"
            response += f"Создан: {template['created_at'][:10]}\n\n"
            response += "Выберите действие:"
            
            bot.send_message(
                message.chat.id,
                response,
                parse_mode="Markdown",
                reply_markup=markup
            )
        return
    
    elif text == "➕ Добавить админа":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'adding_admin'
        
        bot.reply_to(
            message,
            "👤 *Добавление админа*\n\n"
            "Отправьте Telegram ID пользователя:",
            parse_mode="Markdown",
            reply_markup=kb.back_menu_reply()
        )
        return
    
    elif text == "🔧 Управление админами":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        
        admins = db.get_all_admins()
        # Фильтруем супер-админа из списка
        admins = [a for a in admins if a['user_id'] != SUPER_ADMIN_ID]
        
        if not admins:
            bot.reply_to(message, "❌ Нет младших админов для управления")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'selecting_admin'
        
        markup = kb.admins_list_reply(admins)
        bot.send_message(
            message.chat.id,
            "👥 *Выберите админа для управления:*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text.startswith("👤 "):
        # Выбор админа из списка
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        if state.get('state') != 'selecting_admin':
            return
        
        # Извлекаем имя админа
        admin_name = text[2:].strip()  # Убираем "👤 "
        
        # Находим админа по имени или ID
        admins = db.get_all_admins()
        selected_admin = None
        for admin in admins:
            username = admin.get('username') or f"ID: {admin['user_id']}"
            if username == admin_name:
                selected_admin = admin
                break
        
        if not selected_admin:
            bot.reply_to(message, "❌ Админ не найден")
            return
        
        # Сохраняем выбранного админа в состоянии
        state['selected_admin_id'] = selected_admin['user_id']
        state['selected_admin_name'] = admin_name
        state['state'] = 'admin_actions'
        
        # Показываем меню действий
        markup = kb.admin_actions_menu_reply(admin_name)
        channels = db.get_admin_channels(selected_admin['user_id'])
        
        response = f"👤 *Админ: {admin_name}*\n\n"
        response += f"ID: `{selected_admin['user_id']}`\n"
        response += f"Прикреплено каналов: {len(channels)}\n\n"
        response += "Выберите действие:"
        
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔙 К списку админов":
        if not is_super_admin(user_id):
            return
        
        admins = db.get_all_admins()
        admins = [a for a in admins if a['user_id'] != SUPER_ADMIN_ID]
        
        state = get_user_state(user_id)
        state['state'] = 'selecting_admin'
        state.pop('selected_admin_id', None)
        
        markup = kb.admins_list_reply(admins)
        bot.send_message(
            message.chat.id,
            "👥 *Выберите админа для управления:*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    
    elif text == "📊 Статистика админа":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        admin_name = state.get('selected_admin_name')
        
        if not admin_id:
            bot.reply_to(message, "❌ Админ не выбран")
            return
        
        stats = db.get_admin_stats(admin_id)
        response = f"📊 *Статистика админа {admin_name}*\n\n"
        response += f"Всего загрузок: *{stats['total']}*\n\n"
        
        if stats['by_channel']:
            response += "*По каналам:*\n"
            for ch in stats['by_channel']:
                response += f"• {ch['channel_name']}: {ch['count']}\n"
        else:
            response += "Нет загрузок"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    elif text == "📺 Каналы админа":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        admin_name = state.get('selected_admin_name')
        
        if not admin_id:
            bot.reply_to(message, "❌ Админ не выбран")
            return
        
        state['state'] = 'admin_channels'
        
        channels = db.get_admin_channels(admin_id)
        response = f"📺 *Каналы админа {admin_name}*\n\n"
        
        if channels:
            response += "*Прикрепленные каналы:*\n\n"
            for ch in channels:
                response += f"✅ {ch['channel_name']}\n"
        else:
            response += "❌ Нет прикрепленных каналов"
        
        markup = kb.admin_channels_menu_reply()
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔙 К админу":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        admin_name = state.get('selected_admin_name')
        
        if not admin_id:
            return
        
        state['state'] = 'admin_actions'
        
        markup = kb.admin_actions_menu_reply(admin_name)
        channels = db.get_admin_channels(admin_id)
        
        response = f"👤 *Админ: {admin_name}*\n\n"
        response += f"ID: `{admin_id}`\n"
        response += f"Прикреплено каналов: {len(channels)}\n\n"
        response += "Выберите действие:"
        
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "➕ Прикрепить канал":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        
        if not admin_id:
            bot.reply_to(message, "❌ Админ не выбран")
            return
        
        state['state'] = 'attaching_channel'
        
        all_channels = db.get_all_channels()
        attached_channels = db.get_admin_channels(admin_id)
        attached_ids = {ch['channel_id'] for ch in attached_channels}
        
        if not all_channels:
            bot.reply_to(message, "❌ Нет доступных каналов. Сначала добавьте каналы.")
            return
        
        markup = kb.channels_list_for_attach_reply(all_channels, attached_ids)
        bot.send_message(
            message.chat.id,
            "📺 *Управление каналами*\n\n"
            "✅ - канал прикреплен\n"
            "⬜ - канал не прикреплен\n\n"
            "Нажмите на канал для прикрепления/открепления:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔙 К каналам админа":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        admin_name = state.get('selected_admin_name')
        
        if not admin_id:
            return
        
        state['state'] = 'admin_channels'
        
        channels = db.get_admin_channels(admin_id)
        response = f"📺 *Каналы админа {admin_name}*\n\n"
        
        if channels:
            response += "*Прикрепленные каналы:*\n\n"
            for ch in channels:
                response += f"✅ {ch['channel_name']}\n"
        else:
            response += "❌ Нет прикрепленных каналов"
        
        markup = kb.admin_channels_menu_reply()
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text.startswith("✅ ") or text.startswith("⬜ "):
        # Прикрепление/открепление канала к админу
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        
        # Проверяем состояние - это может быть прикрепление к админу или к шаблону
        if state.get('state') == 'attaching_channel':
            # Прикрепление канала к админу (существующий код)
            admin_id = state.get('selected_admin_id')
            if not admin_id:
                return
            
            # Извлекаем название канала
            channel_name = text[2:].strip()  # Убираем "✅ " или "⬜ "
            
            # Находим канал по имени
            all_channels = db.get_all_channels()
            selected_channel = None
            for ch in all_channels:
                if ch['channel_name'] == channel_name:
                    selected_channel = ch
                    break
            
            if not selected_channel:
                bot.reply_to(message, "❌ Канал не найден")
                return
            
            channel_id = selected_channel['channel_id']
            attached_channels = db.get_admin_channels(admin_id)
            attached_ids = {ch['channel_id'] for ch in attached_channels}
            
            # Переключаем состояние прикрепления
            if channel_id in attached_ids:
                # Открепить
                db.unassign_admin_from_channel(admin_id, channel_id)
                action = "откреплен"
            else:
                # Прикрепить
                db.assign_admin_to_channel(admin_id, channel_id)
                action = "прикреплен"
            
            # Обновляем клавиатуру
            attached_channels = db.get_admin_channels(admin_id)
            attached_ids = {ch['channel_id'] for ch in attached_channels}
            markup = kb.channels_list_for_attach_reply(all_channels, attached_ids)
            
            bot.send_message(
                message.chat.id,
                f"✅ Канал *{channel_name}* {action}!\n\n"
                "📺 *Управление каналами*\n\n"
                "✅ - канал прикреплен\n"
                "⬜ - канал не прикреплен\n\n"
                "Нажмите на канал для прикрепления/открепления:",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return
        # Если состояние не 'attaching_channel', пропускаем - обработается позже
        return
    
    elif text == "🗑 Удалить админа":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        admin_id = state.get('selected_admin_id')
        admin_name = state.get('selected_admin_name')
        
        if not admin_id:
            bot.reply_to(message, "❌ Админ не выбран")
            return
        
        # Удаляем админа
        db.remove_admin(admin_id)
        clear_user_state(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ Админ *{admin_name}* удален!",
            parse_mode="Markdown"
        )
        
        # Возвращаемся к списку админов
        admins = db.get_all_admins()
        response = "👥 *Управление админами*\n\n*Список админов:*\n\n"
        for admin in admins:
            username = admin.get('username') or f"ID: {admin['user_id']}"
            is_super = " 👑" if admin['user_id'] == SUPER_ADMIN_ID else ""
            response += f"• {username}{is_super}\n"
        
        markup = kb.admins_menu_reply()
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # ========== УПРАВЛЕНИЕ ШАБЛОНАМИ ==========
    elif text == "📝 Шаблоны":
        if not is_super_admin(user_id):
            bot.reply_to(message, "⛔ Только для супер-админа")
            return
        
        clear_user_state(user_id)
        markup = kb.templates_menu_reply()
        bot.send_message(
            message.chat.id,
            "📝 *Управление шаблонами*\n\n"
            "Шаблоны используются для автоматического форматирования подписей к видео.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "➕ Добавить шаблон":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        state['state'] = 'adding_template_name'
        
        bot.reply_to(
            message,
            "📝 *Создание шаблона*\n\n"
            "Отправьте название шаблона (например: 'Стандартный', 'Для аниме'):",
            parse_mode="Markdown",
            reply_markup=kb.back_menu_reply()
        )
        return
    
    elif text == "📋 Список шаблонов":
        if not is_super_admin(user_id):
            return
        
        templates = db.get_all_templates()
        if not templates:
            bot.reply_to(message, "❌ Нет созданных шаблонов")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'selecting_template'
        
        markup = kb.templates_list_reply(templates)
        bot.send_message(
            message.chat.id,
            "📋 *Список шаблонов*\n\nВыберите шаблон:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔙 К шаблонам":
        if not is_super_admin(user_id):
            return
        
        clear_user_state(user_id)
        markup = kb.templates_menu_reply()
        bot.send_message(
            message.chat.id,
            "📝 *Управление шаблонами*\n\n"
            "Шаблоны используются для автоматического форматирования подписей к видео.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔙 К списку шаблонов":
        if not is_super_admin(user_id):
            return
        
        templates = db.get_all_templates()
        state = get_user_state(user_id)
        state['state'] = 'selecting_template'
        state.pop('selected_template_id', None)
        
        markup = kb.templates_list_reply(templates)
        bot.send_message(
            message.chat.id,
            "📋 *Список шаблонов*\n\nВыберите шаблон:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "👁 Просмотр":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        template_id = state.get('selected_template_id')
        
        if not template_id:
            bot.reply_to(message, "❌ Шаблон не выбран")
            return
        
        template = db.get_template(template_id)
        if not template:
            bot.reply_to(message, "❌ Шаблон не найден")
            return
        
        response = f"📝 *{escape_markdown(template['name'])}*\n\n"
        response += f"*Текст шаблона:*\n\n{escape_markdown(template['template_text'])}\n\n"
        response += "_Переменные:_\n"
        response += "`{title}` - название\n"
        response += "`{season}` - сезон\n"
        response += "`{episode}` - серия\n"
        response += "`{tag}` - тег"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    elif text == "✏️ Редактировать":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        template_id = state.get('selected_template_id')
        
        if not template_id:
            bot.reply_to(message, "❌ Шаблон не выбран")
            return
        
        state['state'] = 'editing_template'
        
        bot.reply_to(
            message,
            "✏️ *Редактирование шаблона*\n\n"
            "Отправьте новый текст шаблона.\n\n"
            "Доступные переменные:\n"
            "`{title}` - название\n"
            "`{season}` - сезон\n"
            "`{episode}` - серия\n"
            "`{tag}` - тег",
            parse_mode="Markdown",
            reply_markup=kb.back_menu_reply()
        )
        return
    
    elif text == "🗑 Удалить шаблон":
        if not is_super_admin(user_id):
            return
        
        state = get_user_state(user_id)
        template_id = state.get('selected_template_id')
        template_name = state.get('selected_template_name')
        
        if not template_id:
            bot.reply_to(message, "❌ Шаблон не выбран")
            return
        
        db.remove_template(template_id)
        clear_user_state(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ Шаблон *{escape_markdown(template_name)}* удален!",
            parse_mode="Markdown"
        )
        
        markup = kb.templates_menu_reply()
        bot.send_message(
            message.chat.id,
            "📝 *Управление шаблонами*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    elif text == "🔗 Прикрепить к каналу":
        if not is_super_admin(user_id):
            return
        
        templates = db.get_all_templates()
        if not templates:
            bot.reply_to(message, "❌ Нет созданных шаблонов. Сначала создайте шаблон.")
            return
        
        state = get_user_state(user_id)
        state['state'] = 'selecting_template_for_channel'
        
        markup = kb.templates_list_reply(templates)
        bot.send_message(
            message.chat.id,
            "📝 *Выберите шаблон для прикрепления:*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # ========== ОБРАБОТКА СОСТОЯНИЙ ==========
    state = get_user_state(user_id)
    
    # Обработка добавления канала
    if state.get('state') == 'adding_channel':
        if not is_super_admin(user_id):
            return
        
        channel_input = message.text.strip()
        
        # Парсим ID канала из различных форматов
        try:
            channel_id = parse_channel_id(channel_input)
            
            # Если это приватная ссылка-приглашение
            if channel_id is None:
                bot.reply_to(
                    message,
                    "⚠️ *Приватная ссылка-приглашение*\n\n"
                    "Вы отправили приватную ссылку-приглашение (с `+`).\n\n"
                    "Для таких каналов нужен числовой ID канала в формате `-1001234567890`.\n\n"
                    "Как получить ID:\n"
                    "1️⃣ Перешлите любое сообщение из канала боту @username_to_id_bot\n"
                    "2️⃣ Или используйте @getmyid_bot\n"
                    "3️⃣ Скопируйте числовой ID и отправьте его сюда\n\n"
                    "Попробуйте еще раз:",
                    parse_mode="Markdown"
                )
                return
                
        except ValueError as e:
            bot.reply_to(
                message,
                "❌ *Неверный формат*\n\n"
                f"Ошибка: {str(e)}\n\n"
                "ID канала должен быть в одном из форматов:\n"
                "• `@channel_username` - для публичных каналов\n"
                "• `https://t.me/channel_username` - ссылка на публичный канал\n"
                "• `-1001234567890` - числовой ID для приватных каналов\n\n"
                "Попробуйте еще раз:",
                parse_mode="Markdown"
            )
            return
        
        # Проверка доступности канала
        try:
            # Пытаемся получить информацию о чате
            chat_info = bot.get_chat(channel_id)
            
            # Проверяем, что это канал
            if chat_info.type not in ['channel', 'supergroup']:
                bot.reply_to(
                    message,
                    f"❌ *Ошибка*\n\n"
                    f"Это не канал! Тип: {chat_info.type}\n\n"
                    f"Отправьте ID канала:",
                    parse_mode="Markdown"
                )
                return
            
            # Проверяем права бота
            try:
                bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
                if bot_member.status not in ['administrator', 'creator']:
                    bot.reply_to(
                        message,
                        "⚠️ *Предупреждение*\n\n"
                        f"Канал найден: *{chat_info.title}*\n\n"
                        "Но бот не является администратором!\n\n"
                        "Добавьте бота в канал как администратора с правом публикации сообщений.\n\n"
                        "Продолжить добавление канала? (да/нет)",
                        parse_mode="Markdown"
                    )
                    state['temp']['channel_id'] = channel_id
                    state['temp']['channel_title'] = chat_info.title
                    state['state'] = 'confirming_channel_without_rights'
                    return
                
                # Проверяем право на публикацию
                if not bot_member.can_post_messages:
                    bot.reply_to(
                        message,
                        "⚠️ *Предупреждение*\n\n"
                        f"Канал найден: *{chat_info.title}*\n\n"
                        "Бот является администратором, но не имеет права публикации сообщений!\n\n"
                        "Дайте боту право 'Публикация сообщений' в настройках канала.\n\n"
                        "Продолжить добавление канала? (да/нет)",
                        parse_mode="Markdown"
                    )
                    state['temp']['channel_id'] = channel_id
                    state['temp']['channel_title'] = chat_info.title
                    state['state'] = 'confirming_channel_without_rights'
                    return
                
            except Exception as e:
                logging.warning(f"Could not check bot permissions: {e}")
            
            # Всё хорошо, запрашиваем название
            state['temp']['channel_id'] = channel_id
            state['temp']['channel_title'] = chat_info.title
            state['state'] = 'adding_channel_name'
            
            bot.reply_to(
                message,
                f"✅ *Канал найден!*\n\n"
                f"Название в Telegram: *{chat_info.title}*\n"
                f"ID: `{channel_id}`\n\n"
                f"Отправьте название для бота (или отправьте '-' чтобы использовать '{chat_info.title}'):",
                parse_mode="Markdown"
            )
            return
            
        except Exception as e:
            error_msg = str(e)
            if "chat not found" in error_msg.lower():
                bot.reply_to(
                    message,
                    "❌ *Канал не найден*\n\n"
                    "Возможные причины:\n"
                    "1️⃣ ID канала указан неверно\n"
                    "2️⃣ Канал приватный и бот не добавлен\n"
                    "3️⃣ Канал не существует\n\n"
                    "Проверьте ID и попробуйте еще раз:",
                    parse_mode="Markdown"
                )
            else:
                bot.reply_to(
                    message,
                    f"❌ *Ошибка при проверке канала*\n\n"
                    f"Детали: `{error_msg}`\n\n"
                    f"Попробуйте еще раз или обратитесь к администратору.",
                    parse_mode="Markdown"
                )
            return
    
    # Подтверждение добавления канала без прав
    elif state.get('state') == 'confirming_channel_without_rights':
        if not is_super_admin(user_id):
            return
        
        answer = message.text.strip().lower()
        if answer in ['да', 'yes', 'y', '+']:
            channel_id = state['temp'].get('channel_id')
            channel_title = state['temp'].get('channel_title')
            state['state'] = 'adding_channel_name'
            
            bot.reply_to(
                message,
                f"📺 Канал: *{channel_title}*\n"
                f"ID: `{channel_id}`\n\n"
                f"Отправьте название для бота (или отправьте '-' чтобы использовать '{channel_title}'):",
                parse_mode="Markdown"
            )
        else:
            clear_user_state(user_id)
            bot.reply_to(message, "❌ Добавление канала отменено")
        return
    
    # Обработка названия канала
    elif state.get('state') == 'adding_channel_name':
        if not is_super_admin(user_id):
            return
        
        channel_id = state['temp'].get('channel_id')
        channel_title = state['temp'].get('channel_title', '')
        channel_name = message.text.strip()
        
        # Если отправлен '-', используем название из Telegram
        if channel_name == '-' and channel_title:
            channel_name = channel_title
        
        if db.add_channel(channel_id, channel_name):
            bot.send_message(
                message.chat.id,
                f"✅ *Канал успешно добавлен!*\n\n"
                f"Название: *{channel_name}*\n"
                f"ID: `{channel_id}`\n\n"
                f"Теперь вы можете прикрепить этот канал к админам.",
                parse_mode="Markdown",
                reply_markup=kb.home_menu_reply()
            )
            logging.info(f"Channel added: {channel_id} - {channel_name}")
        else:
            bot.reply_to(message, "❌ Ошибка при добавлении канала")
        
        clear_user_state(user_id)
        return
    
    # Обработка добавления админа
    elif state.get('state') == 'adding_admin':
        if not is_super_admin(user_id):
            return
        
        try:
            new_admin_id = int(message.text.strip())
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат ID. Отправьте число.")
            return
        
        if new_admin_id == SUPER_ADMIN_ID:
            bot.reply_to(message, "⚠️ Супер-админ уже есть в системе")
            clear_user_state(user_id)
            return
        
        if db.is_admin(new_admin_id):
            bot.reply_to(message, "⚠️ Этот пользователь уже админ")
            clear_user_state(user_id)
            return
        
        # Пытаемся получить информацию о пользователе
        username = None
        try:
            # Пытаемся получить информацию через общий чат с ботом
            user_info = bot.get_chat(new_admin_id)
            username = user_info.username or user_info.first_name or f"ID: {new_admin_id}"
            if user_info.last_name:
                username = f"{user_info.first_name} {user_info.last_name}"
        except Exception as e:
            logging.warning(f"Could not get user info for {new_admin_id}: {e}")
            username = None
        
        if db.add_admin(new_admin_id, username=username):
            display_name = username if username else f"ID: {new_admin_id}"
            bot.send_message(
                message.chat.id,
                f"✅ Админ *{display_name}* успешно добавлен!\n\n"
                f"ID: `{new_admin_id}`\n\n"
                "ℹ️ *Важно:* Новый админ пока не прикреплен ни к одному каналу.\n\n"
                "Чтобы прикрепить каналы:\n"
                "1. Перейдите в 👥 *Админы*\n"
                "2. Нажмите 🔧 *Управление админами*\n"
                "3. Выберите админа\n"
                "4. Нажмите 📺 *Каналы админа*\n"
                "5. Нажмите ➕ *Прикрепить канал*",
                parse_mode="Markdown",
                reply_markup=kb.home_menu_reply()
            )
            logging.info(f"Admin added: {new_admin_id} ({username})")
        else:
            bot.reply_to(message, "❌ Ошибка при добавлении админа")
        
        clear_user_state(user_id)
        return
    
    # Обработка добавления шаблона - название
    elif state.get('state') == 'adding_template_name':
        if not is_super_admin(user_id):
            return
        
        template_name = message.text.strip()
        
        # Проверяем, не существует ли уже такой шаблон
        existing = db.get_template_by_name(template_name)
        if existing:
            bot.reply_to(message, "❌ Шаблон с таким названием уже существует")
            return
        
        state['temp']['template_name'] = template_name
        state['state'] = 'adding_template_text'
        
        bot.reply_to(
            message,
            f"📝 Название: *{escape_markdown(template_name)}*\n\n"
            "Теперь отправьте текст шаблона.\n\n"
            "Доступные переменные:\n"
            "`{title}` - название\n"
            "`{season}` - сезон\n"
            "`{episode}` - серия\n"
            "`{tag}` - тег\n\n"
            "Пример:\n"
            "```\n"
            "🎬 {title}\n"
            "📺 Сезон {season}\n"
            "📺 Серия {episode}\n"
            "{tag}\n"
            "```",
            parse_mode="Markdown"
        )
        return
    
    # Обработка добавления шаблона - текст
    elif state.get('state') == 'adding_template_text':
        if not is_super_admin(user_id):
            return
        
        template_name = state['temp'].get('template_name')
        template_text = message.text
        
        if db.add_template(template_name, template_text):
            bot.send_message(
                message.chat.id,
                f"✅ *Шаблон '{escape_markdown(template_name)}' создан!*\n\n"
                "Теперь вы можете прикрепить его к каналу через меню шаблонов.",
                parse_mode="Markdown",
                reply_markup=kb.home_menu_reply()
            )
            logging.info(f"Template added: {template_name}")
        else:
            bot.reply_to(message, "❌ Ошибка при создании шаблона")
        
        clear_user_state(user_id)
        return
    
    # Обработка редактирования шаблона
    elif state.get('state') == 'editing_template':
        if not is_super_admin(user_id):
            return
        
        template_id = state.get('selected_template_id')
        new_text = message.text
        
        if db.update_template(template_id, template_text=new_text):
            bot.reply_to(message, "✅ Шаблон обновлен!")
            logging.info(f"Template {template_id} updated")
        else:
            bot.reply_to(message, "❌ Ошибка при обновлении шаблона")
        
        clear_user_state(user_id)
        
        # Возвращаемся к меню шаблонов
        markup = kb.templates_menu_reply()
        bot.send_message(
            message.chat.id,
            "📝 *Управление шаблонами*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # Обработка прикрепления шаблона к каналу
    elif state.get('state') == 'assigning_template_to_channel':
        if not is_super_admin(user_id):
            return
        
        # Проверяем, это выбор канала
        if not text.startswith("📺 ") and not text.startswith("✅ "):
            return
        
        channel_name = text.replace("📺 ", "").replace("✅ ", "").strip()
        template_id = state.get('selected_template_id')
        template_name = state.get('selected_template_name')
        
        # Находим канал
        channels = db.get_all_channels()
        selected_channel = None
        for ch in channels:
            if ch['channel_name'] == channel_name:
                selected_channel = ch
                break
        
        if not selected_channel:
            bot.reply_to(message, "❌ Канал не найден")
            return
        
        channel_id = selected_channel['channel_id']
        
        # Проверяем, прикреплен ли уже шаблон к этому каналу
        current_template = db.get_channel_template(channel_id)
        
        if current_template and current_template['id'] == template_id:
            # Открепляем
            db.unassign_template_from_channel(channel_id)
            bot.send_message(
                message.chat.id,
                f"✅ Шаблон *{escape_markdown(template_name)}* откреплен от канала *{escape_markdown(channel_name)}*",
                parse_mode="Markdown"
            )
        else:
            # Прикрепляем
            db.assign_template_to_channel(channel_id, template_id)
            bot.send_message(
                message.chat.id,
                f"✅ Шаблон *{escape_markdown(template_name)}* прикреплен к каналу *{escape_markdown(channel_name)}*",
                parse_mode="Markdown"
            )
        
        # Обновляем список каналов
        assigned_channel_id = None
        for ch in channels:
            ch_template = db.get_channel_template(ch['channel_id'])
            if ch_template and ch_template['id'] == template_id:
                assigned_channel_id = ch['channel_id']
                break
        
        markup = kb.channels_for_template_reply(channels, assigned_channel_id)
        bot.send_message(
            message.chat.id,
            f"📺 *Прикрепление шаблона '{escape_markdown(template_name)}'*\n\n"
            "Выберите канал:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # Обработка информации о серии
    elif state.get('state') == 'waiting_info':
        data = parse_input(message.text)
        if not data:
            bot.reply_to(
                message,
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "• `Название Сезон Серия` - для одной серии\n"
                "• `Название Сезон Серия1-Серия2` - для диапазона\n\n"
                "Примеры:\n"
                "• `Боевой континет 1 12`\n"
                "• `Боевой континет 1 1-12`",
                parse_mode="Markdown"
            )
            return
        
        state['data'] = data
        
        # Получить доступные каналы
        channels = db.get_admin_channels(user_id) if not is_super_admin(user_id) else db.get_all_channels()
        
        if not channels:
            bot.reply_to(message, "❌ Нет доступных каналов")
            clear_user_state(user_id)
            return
        
        # Если канал один - автоматически выбрать
        if len(channels) == 1:
            state['channel_id'] = channels[0]['channel_id']
            state['state'] = 'waiting_video'
            bot.reply_to(
                message,
                f"✅ Информация принята!\n"
                f"📺 Канал: *{channels[0]['channel_name']}*\n\n"
                "Теперь отправьте видео или документ.",
                parse_mode="Markdown"
            )
        else:
            # Показать выбор каналов
            state['state'] = 'selecting_channel'
            markup = kb.channels_select_reply(channels)
            bot.reply_to(
                message,
                "✅ Информация принята!\n\n"
                "Выберите канал для публикации:",
                reply_markup=markup
            )
        return
    
    # Если нет активного состояния - игнорировать
    else:
        return

@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    user_id = message.from_user.id
    logging.info(f"Video from {user_id}")

    if not is_admin(user_id):
        return

    state = get_user_state(user_id)
    
    # Проверка состояния
    if state.get('state') not in ['waiting_video', 'selecting_channel']:
        bot.reply_to(message, "❗ Сначала начните процесс загрузки через меню")
        return
    
    # Если канал еще не выбран
    if not state.get('channel_id'):
        channels = db.get_admin_channels(user_id) if not is_super_admin(user_id) else db.get_all_channels()
        
        if len(channels) == 1:
            state['channel_id'] = channels[0]['channel_id']
        else:
            markup = kb.channels_select_reply(channels)
            bot.reply_to(
                message,
                "Сначала выберите канал:",
                reply_markup=markup
            )
            return
    
    data = state.get('data')
    channel_id = state.get('channel_id')
    
    if not data:
        bot.reply_to(message, "❗ Сначала отправьте описание серии")
        return
    
    # Проверка прав на канал
    if not is_super_admin(user_id):
        admin_channels = db.get_admin_channels(user_id)
        if not any(ch['channel_id'] == channel_id for ch in admin_channels):
            bot.reply_to(message, "⛔ У вас нет доступа к этому каналу")
            clear_user_state(user_id)
            return

    # Проверка размера файла - ОТКЛЮЧЕНА
    # file_size = None
    # if message.content_type == 'video':
    #     file_size = getattr(message.video, 'file_size', None)
    # else:
    #     file_size = getattr(message.document, 'file_size', None)
    
    # if file_size and file_size > MAX_FILE_SIZE:
    #     mb = MAX_FILE_SIZE // (1024 * 1024)
    #     bot.reply_to(message, f"❌ Файл слишком большой. Макс: {mb} MB")
    #     clear_user_state(user_id)
    #     return
    
    # Формирование подписи
    # Проверяем, есть ли шаблон для этого канала
    template = db.get_channel_template(channel_id)
    
    if template:
        # Используем шаблон
        caption = template['template_text']
        
        # Заменяем переменные
        caption = caption.replace('{title}', data['title'])
        caption = caption.replace('{season}', str(data['season']))
        
        # Для серии - если диапазон, показываем диапазон
        if data.get('is_range'):
            episode_str = f"{data['episode_start']}-{data['episode_end']}"
        else:
            episode_str = str(data['episode'])
        caption = caption.replace('{episode}', episode_str)
        caption = caption.replace('{tag}', data['tag'])
        
        logging.info(f"Using template '{template['name']}' for channel {channel_id}")
    else:
        # Используем стандартный формат
        if data.get('is_range'):
            episode_text = f"📺 Серии {data['episode_start']}-{data['episode_end']}"
        else:
            episode_text = f"📺 Серия {data['episode']}"
            
        caption = (
            f"🎬 {data['title']}\n\n"
            f"📺 Сезон {data['season']}\n"
            f"{episode_text}\n\n"
            f"{data['tag']}\n\n"
            "Наш канал: https://t.me/+XaaureBEZzMwNDk6\n"
            "Наш чат: https://t.me/Anume2D"
        )
        logging.info(f"Using default caption format for channel {channel_id}")

    try:
        # Отправка в канал
        sent = None
        sent_file_id = None
        if message.content_type == 'video':
            sent_file_id = message.video.file_id
            sent = bot.send_video(channel_id, sent_file_id, caption=caption)
        else:
            sent_file_id = message.document.file_id
            sent = bot.send_document(channel_id, sent_file_id, caption=caption)
        
        # Получить id сообщения в канале (если доступно)
        message_id = str(getattr(sent, 'message_id', None)) if sent else None

        # Логирование в статистику
        # Если диапазон - логируем среднюю серию или начальную
        episode_for_log = data.get('episode') or data.get('episode_start', 0)
        
        db.log_upload(
            user_id,
            channel_id,
            data['title'],
            int(data['season']),
            int(episode_for_log),
            file_id=sent_file_id,
            message_id=message_id
        )
        
        channel = db.get_channel(channel_id)
        
        # Формируем строку для логирования
        if data.get('is_range'):
            episode_log = f"S{data['season']}E{data['episode_start']}-{data['episode_end']}"
        else:
            episode_log = f"S{data['season']}E{data['episode']}"
            
        logging.info(
            f"Published | {data['title']} | {episode_log} | "
            f"Channel: {channel['channel_name']} | Admin: {user_id} | msg_id={message_id}"
        )
        
        bot.reply_to(
            message,
            f"🎉 Серия опубликована в канал *{channel['channel_name']}*!",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error publishing video: {e}")
        
        # Определяем тип ошибки и даем понятное объяснение
        if "chat not found" in error_message.lower():
            channel = db.get_channel(channel_id)
            channel_name = channel['channel_name'] if channel else channel_id
            
            bot.reply_to(
                message,
                f"❌ *Ошибка публикации*\n\n"
                f"Канал не найден: *{channel_name}*\n"
                f"ID канала: `{channel_id}`\n\n"
                f"*Возможные причины:*\n"
                f"1️⃣ Бот не добавлен в канал\n"
                f"2️⃣ ID канала указан неверно\n"
                f"3️⃣ Канал был удален\n\n"
                f"*Решение:*\n"
                f"• Добавьте бота в канал как администратора\n"
                f"• Дайте боту права на публикацию сообщений\n"
                f"• Проверьте правильность ID канала",
                parse_mode="Markdown"
            )
        elif "bot was kicked" in error_message.lower() or "forbidden" in error_message.lower():
            channel = db.get_channel(channel_id)
            channel_name = channel['channel_name'] if channel else channel_id
            
            bot.reply_to(
                message,
                f"❌ *Ошибка публикации*\n\n"
                f"Бот заблокирован в канале: *{channel_name}*\n\n"
                f"*Решение:*\n"
                f"• Разблокируйте бота в канале\n"
                f"• Добавьте бота обратно как администратора",
                parse_mode="Markdown"
            )
        elif "not enough rights" in error_message.lower():
            channel = db.get_channel(channel_id)
            channel_name = channel['channel_name'] if channel else channel_id
            
            bot.reply_to(
                message,
                f"❌ *Ошибка публикации*\n\n"
                f"Недостаточно прав в канале: *{channel_name}*\n\n"
                f"*Решение:*\n"
                f"• Дайте боту права администратора\n"
                f"• Включите право 'Публикация сообщений'",
                parse_mode="Markdown"
            )
        else:
            # Общая ошибка
            bot.reply_to(
                message, 
                f"❌ *Ошибка при публикации*\n\n"
                f"Детали: `{error_message}`\n\n"
                f"Обратитесь к администратору.",
                parse_mode="Markdown"
            )
    
    clear_user_state(user_id)


# ========== TEXT COMMANDS (admin utilities) ==========
@bot.message_handler(commands=['assign_channel'])
def cmd_assign_channel(message):
    user_id = message.from_user.id
    if not is_super_admin(user_id):
        bot.reply_to(message, "⛔ Только для супер-админа")
        return

    parts = message.text.strip().split()
    if len(parts) != 3:
        bot.reply_to(message, "Использование: /assign_channel <admin_id> <channel_id>")
        return

    try:
        admin_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "admin_id должен быть числом")
        return

    channel_id = parts[2]
    ch = db.get_channel(channel_id)
    if not ch:
        db.add_channel(channel_id, channel_id)

    db.assign_admin_to_channel(admin_id, channel_id)
    bot.reply_to(message, f"✅ Назначено: {admin_id} -> {channel_id}")


@bot.message_handler(commands=['revoke_channel'])
def cmd_revoke_channel(message):
    user_id = message.from_user.id
    if not is_super_admin(user_id):
        bot.reply_to(message, "⛔ Только для супер-админа")
        return

    parts = message.text.strip().split()
    if len(parts) != 3:
        bot.reply_to(message, "Использование: /revoke_channel <admin_id> <channel_id>")
        return

    try:
        admin_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "admin_id должен быть числом")
        return

    channel_id = parts[2]
    db.unassign_admin_from_channel(admin_id, channel_id)
    bot.reply_to(message, f"✅ Убрано: {admin_id} -/-> {channel_id}")


@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    user_id = message.from_user.id
    if not is_super_admin(user_id):
        bot.reply_to(message, "⛔ Только для супер-админа")
        return

    parts = message.text.strip().split()
    if len(parts) == 1:
        stats = db.get_all_stats()
        text = "📊 *Общая статистика*\n\n"
        if not stats:
            text += "❌ Нет данных"
        else:
            for s in stats:
                username = s.get('username') or f"ID: {s['user_id']}"
                total = s['total_uploads']
                text += f"• {username}: *{total}* загрузок\n"
        bot.reply_to(message, text, parse_mode="Markdown")
        return

    # stats for specific admin
    try:
        admin_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "admin_id должен быть числом")
        return

    stats = db.get_admin_stats(admin_id)
    text = f"📊 *Статистика админа {admin_id}*\n\n"
    text += f"Всего загрузок: *{stats['total']}*\n\n"
    if stats['by_channel']:
        text += "*По каналам:*\n"
        for ch in stats['by_channel']:
            text += f"• {ch['channel_name']}: {ch['count']}\n"
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=['my_channels'])
def cmd_my_channels(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    channels = db.get_admin_channels(user_id)
    text = "📺 *Мои каналы*\n\n"
    if not channels:
        text += "❌ Вы не назначены ни на один канал"
    else:
        for ch in channels:
            text += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=['my_stats'])
def cmd_my_stats(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    stats = db.get_admin_stats(user_id)
    text = f"📊 *Моя статистика*\n\n"
    text += f"Всего загрузок: *{stats['total']}*\n\n"
    if stats['by_channel']:
        text += "*По каналам:*\n"
        for ch in stats['by_channel']:
            text += f"• {ch['channel_name']}: {ch['count']}\n"

    bot.reply_to(message, text, parse_mode="Markdown")


# ================== RUN ==================
if __name__ == '__main__':
    import time
    from requests.exceptions import ConnectionError, Timeout, ReadTimeout
    
    print("🤖 Бот запускается...")
    logging.info("Bot starting...")
    
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            print("✅ Бот запущен и готов к работе!")
            logging.info("Bot is running...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
            
        except (ConnectionError, Timeout, ReadTimeout) as e:
            retry_count += 1
            wait_time = min(retry_count * 5, 60)  # Максимум 60 секунд
            
            print(f"⚠️ Ошибка соединения (попытка {retry_count}/{max_retries})")
            logging.warning(f"Connection error: {e}. Retrying in {wait_time}s...")
            
            if retry_count >= max_retries:
                print(f"❌ Превышено количество попыток переподключения")
                logging.error("Max retries exceeded. Exiting...")
                break
            
            time.sleep(wait_time)
            print(f"🔄 Переподключение...")
            
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен пользователем")
            logging.info("Bot stopped by user")
            break
            
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            logging.exception("Critical error occurred")
            
            # Пытаемся уведомить супер-админа
            try:
                send_super_admin_alert(f"🔥 Критическая ошибка бота:\n\n`{str(e)[:200]}`")
            except:
                pass
            
            # Ждем перед перезапуском
            time.sleep(10)
            print("🔄 Попытка перезапуска...")
            retry_count = 0  # Сбрасываем счетчик для критических ошибок
