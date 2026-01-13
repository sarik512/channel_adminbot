from telebot import types
from typing import List, Dict, Optional

# ================== REPLY KEYBOARDS (обычные кнопки) ==================

def main_menu_reply(is_super_admin: bool) -> types.ReplyKeyboardMarkup:
    """Главное меню с обычными кнопками (разное для супер-админа и обычного админа)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if is_super_admin:
        markup.add(
            types.KeyboardButton("📊 Статистика"),
            types.KeyboardButton("📺 Каналы")
        )
        markup.add(
            types.KeyboardButton("👥 Админы"),
            types.KeyboardButton("📝 Шаблоны")
        )
        markup.add(
            types.KeyboardButton("📤 Загрузить")
        )
    else:
        markup.add(
            types.KeyboardButton("📤 Загрузить контент")
        )
        markup.add(
            types.KeyboardButton("📺 Мои каналы"),
            types.KeyboardButton("📊 Моя статистика")
        )
    
    return markup

def back_menu_reply() -> types.ReplyKeyboardMarkup:
    """Кнопка назад"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 НАЗАД"))
    return markup

def home_menu_reply() -> types.ReplyKeyboardMarkup:
    """Кнопка в главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🏠 Главное меню"))
    return markup

def channels_menu_reply() -> types.ReplyKeyboardMarkup:
    """Меню управления каналами с обычными кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ Добавить канал"),
        types.KeyboardButton("🗑 Удалить канал")
    )
    markup.add(
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def admins_menu_reply() -> types.ReplyKeyboardMarkup:
    """Меню управления админами с обычными кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ Добавить админа"),
        types.KeyboardButton("🔧 Управление админами")
    )
    markup.add(
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def admin_actions_menu_reply(admin_name: str) -> types.ReplyKeyboardMarkup:
    """Меню действий для конкретного админа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📊 Статистика админа"),
        types.KeyboardButton("📺 Каналы админа")
    )
    markup.add(
        types.KeyboardButton("🗑 Удалить админа")
    )
    markup.add(
        types.KeyboardButton("🔙 К списку админов"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def admin_channels_menu_reply() -> types.ReplyKeyboardMarkup:
    """Меню управления каналами админа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ Прикрепить канал")
    )
    markup.add(
        types.KeyboardButton("🔙 К админу"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def admins_list_reply(admins: List[Dict]) -> types.ReplyKeyboardMarkup:
    """Список админов для выбора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for admin in admins:
        username = admin.get('username') or f"ID: {admin['user_id']}"
        # Используем формат: 👤 Username
        markup.add(types.KeyboardButton(f"👤 {username}"))
    
    markup.add(
        types.KeyboardButton("🔙 НАЗАД"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def channels_list_for_attach_reply(channels: List[Dict], attached_ids: set) -> types.ReplyKeyboardMarkup:
    """Список каналов для прикрепления/открепления"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    for channel in channels:
        channel_name = channel['channel_name']
        channel_id = channel['channel_id']
        
        if channel_id in attached_ids:
            # Канал уже прикреплен - показываем с галочкой
            markup.add(types.KeyboardButton(f"✅ {channel_name}"))
        else:
            # Канал не прикреплен
            markup.add(types.KeyboardButton(f"⬜ {channel_name}"))
    
    markup.row(
        types.KeyboardButton("🔙 К каналам админа"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def channels_select_reply(channels: List[Dict]) -> types.ReplyKeyboardMarkup:
    """Список каналов для выбора при загрузке видео"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    for channel in channels:
        channel_name = channel['channel_name']
        markup.add(types.KeyboardButton(f"📺 {channel_name}"))
    
    markup.add(types.KeyboardButton("🔙 Главное меню"))
    return markup

def templates_menu_reply() -> types.ReplyKeyboardMarkup:
    """Меню управления шаблонами"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ Добавить шаблон"),
        types.KeyboardButton("📋 Список шаблонов")
    )
    markup.add(
        types.KeyboardButton("🔗 Прикрепить к каналу")
    )
    markup.add(
        types.KeyboardButton("🔙 Главное меню")
    )
    return markup

def templates_list_reply(templates: List[Dict]) -> types.ReplyKeyboardMarkup:
    """Список шаблонов для выбора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for template in templates:
        markup.add(types.KeyboardButton(f"📝 {template['name']}"))
    
    markup.add(
        types.KeyboardButton("🔙 К шаблонам"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def template_actions_menu_reply(template_name: str) -> types.ReplyKeyboardMarkup:
    """Меню действий для конкретного шаблона"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("👁 Просмотр"),
        types.KeyboardButton("✏️ Редактировать")
    )
    markup.add(
        types.KeyboardButton("🗑 Удалить шаблон")
    )
    markup.add(
        types.KeyboardButton("🔙 К списку шаблонов"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup

def channels_for_template_reply(channels: List[Dict], assigned_channel_id: str = None) -> types.ReplyKeyboardMarkup:
    """Список каналов для прикрепления шаблона"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    for channel in channels:
        channel_id = channel['channel_id']
        channel_name = channel['channel_name']
        
        if channel_id == assigned_channel_id:
            markup.add(types.KeyboardButton(f"✅ {channel_name}"))
        else:
            markup.add(types.KeyboardButton(f"📺 {channel_name}"))
    
    markup.row(
        types.KeyboardButton("🔙 К шаблонам"),
        types.KeyboardButton("🏠 Главное меню")
    )
    return markup



# ================== INLINE KEYBOARDS (инлайн кнопки) ==================

def main_menu(is_super_admin: bool) -> types.InlineKeyboardMarkup:
    """Главное меню (разное для супер-админа и обычного админа)"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if is_super_admin:
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats:all"),
            types.InlineKeyboardButton("📺 Каналы", callback_data="menu:channels")
        )
        markup.add(
            types.InlineKeyboardButton("👥 Админы", callback_data="menu:admins"),
            types.InlineKeyboardButton("📤 Загрузить", callback_data="upload:start")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📤 Загрузить контент", callback_data="upload:start")
        )
        markup.add(
            types.InlineKeyboardButton("📺 Мои каналы", callback_data="my:channels"),
            types.InlineKeyboardButton("📊 Моя статистика", callback_data="stats:my")
        )
    
    return markup

def channels_menu() -> types.InlineKeyboardMarkup:
    """Меню управления каналами"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить канал", callback_data="channel:add"),
        types.InlineKeyboardButton("📋 Список каналов", callback_data="channel:list")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:main")
    )
    return markup

def admins_menu() -> types.InlineKeyboardMarkup:
    """Меню управления админами"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить админа", callback_data="admin:add"),
        types.InlineKeyboardButton("📋 Список админов", callback_data="admin:list")
    )
    markup.add(
        types.InlineKeyboardButton("🔗 Назначить на канал", callback_data="admin:assign_menu"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:main")
    )
    return markup

def channel_list_keyboard(channels: List[Dict], action: str = "view") -> types.InlineKeyboardMarkup:
    """
    Список каналов с кнопками действий
    action: 'view', 'delete', 'select', 'assign'
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not channels:
        markup.add(
            types.InlineKeyboardButton("❌ Нет каналов", callback_data="noop")
        )
    else:
        for channel in channels:
            channel_id = channel['channel_id']
            channel_name = channel['channel_name']
            
            if action == "delete":
                text = f"🗑 {channel_name}"
                callback = f"channel:del:{channel_id}"
            elif action == "select":
                text = f"📺 {channel_name}"
                callback = f"channel:select:{channel_id}"
            elif action == "stats":
                text = f"📊 {channel_name}"
                callback = f"stats:channel:{channel_id}"
            elif action == "assign":
                text = f"🔗 {channel_name}"
                callback = f"channel:assign:{channel_id}"
            else:  # view
                text = f"📺 {channel_name} (ID: {channel_id})"
                callback = f"channel:info:{channel_id}"
            
            markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:channels")
    )
    return markup

def admin_list_keyboard(admins: List[Dict], action: str = "view") -> types.InlineKeyboardMarkup:
    """
    Список админов с кнопками действий
    action: 'view', 'delete', 'stats', 'assign'
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not admins:
        markup.add(
            types.InlineKeyboardButton("❌ Нет админов", callback_data="noop")
        )
    else:
        for admin in admins:
            user_id = admin['user_id']
            username = admin.get('username') or f"ID: {user_id}"
            
            if action == "delete":
                text = f"🗑 {username}"
                callback = f"admin:del:{user_id}"
            elif action == "stats":
                text = f"📊 {username}"
                callback = f"stats:admin:{user_id}"
            elif action == "assign":
                text = f"🔗 {username}"
                callback = f"admin:assign:{user_id}"
            else:  # view
                text = f"👤 {username}"
                callback = f"admin:info:{user_id}"
            
            markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:admins")
    )
    return markup

def confirm_keyboard(action: str, item_id: str) -> types.InlineKeyboardMarkup:
    """Подтверждение действия"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да", callback_data=f"confirm:{action}:{item_id}"),
        types.InlineKeyboardButton("❌ Нет", callback_data="menu:main")
    )
    return markup

def back_button(callback_data: str = "menu:main") -> types.InlineKeyboardMarkup:
    """Простая кнопка 'Назад'"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data=callback_data)
    )
    return markup

def stats_menu(is_super_admin: bool) -> types.InlineKeyboardMarkup:
    """Меню статистики"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if is_super_admin:
        markup.add(
            types.InlineKeyboardButton("📊 Общая статистика", callback_data="stats:all"),
            types.InlineKeyboardButton("👤 По админам", callback_data="stats:admins_list"),
            types.InlineKeyboardButton("📺 По каналам", callback_data="stats:channels_list")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📊 Моя статистика", callback_data="stats:my")
        )
    
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:main")
    )
    return markup

def assign_channels_keyboard(admin_id: int, all_channels: List[Dict], assigned_channels: List[Dict]) -> types.InlineKeyboardMarkup:
    """Клавиатура для назначения админа на каналы"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    assigned_ids = {ch['channel_id'] for ch in assigned_channels}
    
    for channel in all_channels:
        channel_id = channel['channel_id']
        channel_name = channel['channel_name']
        
        if channel_id in assigned_ids:
            text = f"✅ {channel_name}"
            callback = f"unassign:{admin_id}:{channel_id}"
        else:
            text = f"⬜ {channel_name}"
            callback = f"assign:{admin_id}:{channel_id}"
        
        markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu:admins")
    )
    return markup

def cancel_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопка отмены"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("❌ Отмена", callback_data="menu:main")
    )
    return markup
