"""
Обработчики управления админами для асинхронного бота
"""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

import database_async as db
from main_async import (
    AdminStates, is_super_admin, is_admin_check, SUPER_ADMIN_ID,
    escape_markdown, main_menu_keyboard, back_and_home_keyboard
)
import logging

router = Router()


def admins_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню управления админами"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить админа"), KeyboardButton(text="🔧 Управление админами")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def admin_actions_keyboard() -> ReplyKeyboardMarkup:
    """Меню действий с админом"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика админа"), KeyboardButton(text="📺 Каналы админа")],
            [KeyboardButton(text="🗑 Удалить админа")],
            [KeyboardButton(text="🔙 К списку админов"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def admin_channels_keyboard() -> ReplyKeyboardMarkup:
    """Меню управления каналами админа"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Прикрепить канал")],
            [KeyboardButton(text="🔙 К админу"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "👥 Админы")
async def btn_admins(message: Message):
    """Меню управления админами"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    admins = await db.get_all_admins()
    response = "👥 *Управление админами*\n\n*Список админов:*\n\n"
    
    for admin in admins:
        username = admin.get('username') or f"ID: {admin['user_id']}"
        username_safe = escape_markdown(username)
        is_super = " 👑" if admin['user_id'] == SUPER_ADMIN_ID else ""
        response += f"• {username_safe}{is_super}\n"
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=admins_menu_keyboard()
    )


@router.message(F.text == "➕ Добавить админа")
async def btn_add_admin(message: Message, state: FSMContext):
    """Начало добавления админа"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    await state.set_state(AdminStates.adding_admin)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 НАЗАД")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "👤 *Добавление админа*\n\n"
        "Отправьте ID пользователя (число):",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(AdminStates.adding_admin, F.text)
async def process_add_admin(message: Message, state: FSMContext):
    """Обработка добавления админа"""
    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "ID должен быть числом. Попробуйте еще раз:"
        )
        return
    
    # Проверяем, не добавлен ли уже
    existing = await db.get_admin(new_admin_id)
    if existing:
        await message.answer(
            f"⚠️ Пользователь уже является админом!\n\n"
            f"ID: {new_admin_id}"
        )
        await state.clear()
        return
    
    # Добавляем админа
    success = await db.add_admin(new_admin_id, username=None, role='junior')
    
    if success:
        logging.info(f"Admin added: {new_admin_id}")
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ *Админ добавлен!*\n\n"
            f"🆔 ID: `{new_admin_id}`\n\n"
            f"ℹ️ Теперь этот пользователь может использовать бота.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при добавлении админа")
    
    await state.clear()


@router.message(F.text == "🔧 Управление админами")
async def btn_manage_admins(message: Message, state: FSMContext):
    """Список админов для управления"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    admins = await db.get_all_admins()
    
    # Исключаем супер-админа из списка
    admins = [a for a in admins if a['user_id'] != SUPER_ADMIN_ID]
    
    if not admins:
        await message.answer("❌ Нет админов для управления")
        return
    
    await state.set_state(AdminStates.selecting_admin)
    
    # Создаем клавиатуру с админами
    buttons = []
    for admin in admins:
        username = admin.get('username') or f"ID: {admin['user_id']}"
        buttons.append([KeyboardButton(text=f"👤 {username}")])
    buttons.append([
        KeyboardButton(text="🔙 НАЗАД"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "👥 *Выберите админа:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(AdminStates.selecting_admin, F.text.startswith("👤 "))
async def process_select_admin(message: Message, state: FSMContext):
    """Обработка выбора админа"""
    admin_identifier = message.text[2:].strip()  # Убираем "👤 "
    
    # Ищем админа
    admins = await db.get_all_admins()
    selected_admin = None
    
    for admin in admins:
        username = admin.get('username') or f"ID: {admin['user_id']}"
        if username == admin_identifier:
            selected_admin = admin
            break
    
    if not selected_admin:
        await message.answer("❌ Админ не найден")
        return
    
    # Сохраняем выбранного админа
    await state.update_data(selected_admin_id=selected_admin['user_id'])
    await state.set_state(AdminStates.admin_actions)
    
    # Показываем меню действий
    username = selected_admin.get('username') or f"ID: {selected_admin['user_id']}"
    
    await message.answer(
        f"👤 *Админ: {username}*\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_actions_keyboard()
    )


@router.message(AdminStates.admin_actions, F.text == "📊 Статистика админа")
async def btn_admin_stats(message: Message, state: FSMContext):
    """Показать статистику админа"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    if not admin_id:
        await message.answer("❌ Ошибка: админ не выбран")
        await state.clear()
        return
    
    admin = await db.get_admin(admin_id)
    stats = await db.get_admin_stats(admin_id)
    
    username = admin.get('username') or f"ID: {admin_id}"
    response = f"📊 *Статистика админа {username}*\n\n"
    response += f"Всего загрузок: *{stats['total']}*\n\n"
    
    if stats['by_channel']:
        response += "*По каналам:*\n"
        for ch in stats['by_channel']:
            response += f"• {ch['channel_name']}: {ch['count']}\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(AdminStates.admin_actions, F.text == "📺 Каналы админа")
async def btn_admin_channels(message: Message, state: FSMContext):
    """Показать каналы админа"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    if not admin_id:
        await message.answer("❌ Ошибка: админ не выбран")
        await state.clear()
        return
    
    admin = await db.get_admin(admin_id)
    channels = await db.get_admin_channels(admin_id)
    
    username = admin.get('username') or f"ID: {admin_id}"
    response = f"📺 *Каналы админа {username}*\n\n"
    
    if not channels:
        response += "❌ Админ не назначен ни на один канал"
    else:
        for ch in channels:
            response += f"• {ch['channel_name']}\n"
    
    await state.set_state(AdminStates.admin_channels)
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=admin_channels_keyboard()
    )


@router.message(AdminStates.admin_channels, F.text == "➕ Прикрепить канал")
async def btn_attach_channel(message: Message, state: FSMContext):
    """Начало прикрепления канала к админу"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    if not admin_id:
        await message.answer("❌ Ошибка: админ не выбран")
        await state.clear()
        return
    
    # Получаем все каналы и каналы админа
    all_channels = await db.get_all_channels()
    admin_channels = await db.get_admin_channels(admin_id)
    
    if not all_channels:
        await message.answer("❌ Нет доступных каналов")
        return
    
    # ID прикрепленных каналов
    attached_ids = {ch['channel_id'] for ch in admin_channels}
    
    await state.set_state(AdminStates.attaching_channel)
    
    # Создаем клавиатуру с каналами
    buttons = []
    for ch in all_channels:
        if ch['channel_id'] in attached_ids:
            buttons.append([KeyboardButton(text=f"✅ {ch['channel_name']}")])
        else:
            buttons.append([KeyboardButton(text=f"⬜ {ch['channel_name']}")])
    
    buttons.append([
        KeyboardButton(text="🔙 К каналам админа"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "📺 *Прикрепление каналов*\n\n"
        "Выберите канал для прикрепления/открепления:\n"
        "✅ - прикреплен\n"
        "⬜ - не прикреплен",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(AdminStates.attaching_channel, F.text.regexp(r"^[✅⬜] "))
async def process_attach_channel(message: Message, state: FSMContext):
    """Обработка прикрепления/открепления канала"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    is_attached = message.text.startswith("✅")
    channel_name = message.text[2:].strip()  # Убираем "✅ " или "⬜ "
    
    # Ищем канал
    all_channels = await db.get_all_channels()
    selected_channel = None
    
    for ch in all_channels:
        if ch['channel_name'] == channel_name:
            selected_channel = ch
            break
    
    if not selected_channel:
        await message.answer("❌ Канал не найден")
        return
    
    # Прикрепляем или открепляем
    if is_attached:
        # Открепляем
        success = await db.unassign_admin_from_channel(admin_id, selected_channel['channel_id'])
        action = "откреплен"
    else:
        # Прикрепляем
        success = await db.assign_admin_to_channel(admin_id, selected_channel['channel_id'])
        action = "прикреплен"
    
    if success:
        # Обновляем клавиатуру
        admin_channels = await db.get_admin_channels(admin_id)
        attached_ids = {ch['channel_id'] for ch in admin_channels}
        
        buttons = []
        for ch in all_channels:
            if ch['channel_id'] in attached_ids:
                buttons.append([KeyboardButton(text=f"✅ {ch['channel_name']}")])
            else:
                buttons.append([KeyboardButton(text=f"⬜ {ch['channel_name']}")])
        
        buttons.append([
            KeyboardButton(text="🔙 К каналам админа"),
            KeyboardButton(text="🏠 Главное меню")
        ])
        
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        
        await message.answer(
            f"✅ Канал *{channel_name}* {action}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer(f"❌ Ошибка при изменении прикрепления канала")


@router.message(AdminStates.attaching_channel, F.text == "🔙 К каналам админа")
async def btn_back_to_admin_channels(message: Message, state: FSMContext):
    """Возврат к каналам админа"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    admin = await db.get_admin(admin_id)
    channels = await db.get_admin_channels(admin_id)
    
    username = admin.get('username') or f"ID: {admin_id}"
    response = f"📺 *Каналы админа {username}*\n\n"
    
    if not channels:
        response += "❌ Админ не назначен ни на один канал"
    else:
        for ch in channels:
            response += f"• {ch['channel_name']}\n"
    
    await state.set_state(AdminStates.admin_channels)
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=admin_channels_keyboard()
    )


@router.message(AdminStates.admin_channels, F.text == "🔙 К админу")
async def btn_back_to_admin(message: Message, state: FSMContext):
    """Возврат к админу"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    admin = await db.get_admin(admin_id)
    username = admin.get('username') or f"ID: {admin_id}"
    
    await state.set_state(AdminStates.admin_actions)
    
    await message.answer(
        f"👤 *Админ: {username}*\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_actions_keyboard()
    )


@router.message(AdminStates.admin_actions, F.text == "🗑 Удалить админа")
async def btn_delete_admin(message: Message, state: FSMContext):
    """Удаление админа"""
    state_data = await state.get_data()
    admin_id = state_data.get('selected_admin_id')
    
    if not admin_id:
        await message.answer("❌ Ошибка: админ не выбран")
        await state.clear()
        return
    
    admin = await db.get_admin(admin_id)
    username = admin.get('username') or f"ID: {admin_id}"
    
    # Удаляем админа
    success = await db.remove_admin(admin_id)
    
    if success:
        logging.info(f"Admin deleted: {admin_id}")
        
        keyboard = main_menu_keyboard(True)
        
        await message.answer(
            f"✅ *Админ удален*\n\n"
            f"👤 {username}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при удалении админа")
    
    await state.clear()


@router.message(AdminStates.admin_actions, F.text == "🔙 К списку админов")
async def btn_back_to_admins_list(message: Message, state: FSMContext):
    """Возврат к списку админов"""
    admins = await db.get_all_admins()
    admins = [a for a in admins if a['user_id'] != SUPER_ADMIN_ID]
    
    if not admins:
        await message.answer("❌ Нет админов для управления")
        await state.clear()
        return
    
    await state.set_state(AdminStates.selecting_admin)
    
    buttons = []
    for admin in admins:
        username = admin.get('username') or f"ID: {admin['user_id']}"
        buttons.append([KeyboardButton(text=f"👤 {username}")])
    buttons.append([
        KeyboardButton(text="🔙 НАЗАД"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "👥 *Выберите админа:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
