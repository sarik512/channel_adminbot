"""
Обработчики управления каналами для асинхронного бота
"""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

import database_async as db
from main_async import (
    ChannelStates, is_super_admin, is_admin_check,
    escape_markdown, bot, back_and_home_keyboard, main_menu_keyboard
)
from utils import parse_channel_id
import logging

router = Router()


def channels_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню управления каналами"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить канал"), KeyboardButton(text="🗑 Удалить канал")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "📺 Каналы")
async def btn_channels(message: Message):
    """Меню управления каналами"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    channels = await db.get_all_channels()
    response = "📺 *Управление каналами*\n\n"
    
    if not channels:
        response += "❌ Нет добавленных каналов\n\n"
        response += "Используйте кнопку '➕ Добавить канал' для добавления."
    else:
        response += "*Список каналов:*\n\n"
        for ch in channels:
            response += f"• {ch['channel_name']}\n"
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=channels_menu_keyboard()
    )


@router.message(F.text == "➕ Добавить канал")
async def btn_add_channel(message: Message, state: FSMContext):
    """Начало добавления канала"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    await state.set_state(ChannelStates.adding_channel)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 НАЗАД")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "📺 *Добавление канала*\n\n"
        "Отправьте ID или ссылку на канал:\n\n"
        "Форматы:\n"
        "• `@channel_username` - публичный канал\n"
        "• `https://t.me/channel_username` - ссылка на публичный канал\n"
        "• `-1001234567890` - числовой ID приватного канала\n\n"
        "❗ Для приватных ссылок (с `+`) используйте числовой ID",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(ChannelStates.adding_channel, F.text)
async def process_add_channel(message: Message, state: FSMContext):
    """Обработка добавления канала"""
    user_id = message.from_user.id
    channel_input = message.text.strip()
    
    # Парсим ID канала
    try:
        channel_id = parse_channel_id(channel_input)
        
        # Если это приватная ссылка-приглашение
        if channel_id is None:
            await message.answer(
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
        await message.answer(
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
        chat_info = await bot.get_chat(channel_id)
        
        # Проверяем, что это канал
        if chat_info.type not in ['channel', 'supergroup']:
            await message.answer(
                f"❌ *Ошибка*\n\n"
                f"Это не канал! Тип: {chat_info.type}\n\n"
                f"Отправьте ID канала:",
                parse_mode="Markdown"
            )
            return
        
        # Проверяем права бота
        try:
            bot_member = await bot.get_chat_member(channel_id, bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await message.answer(
                    "⚠️ *Предупреждение*\n\n"
                    f"Канал найден: *{chat_info.title}*\n\n"
                    "Но бот не является администратором!\n\n"
                    "Добавьте бота в канал как администратора с правом публикации сообщений.\n\n"
                    "Продолжить добавление канала? (да/нет)",
                    parse_mode="Markdown"
                )
                await state.update_data(
                    channel_id=channel_id,
                    channel_title=chat_info.title
                )
                await state.set_state(ChannelStates.confirming_channel_without_rights)
                return
            
            # Проверяем право на публикацию
            if hasattr(bot_member, 'can_post_messages') and not bot_member.can_post_messages:
                await message.answer(
                    "⚠️ *Предупреждение*\n\n"
                    f"Канал найден: *{chat_info.title}*\n\n"
                    "Бот является администратором, но не имеет права публикации сообщений!\n\n"
                    "Дайте боту право 'Публикация сообщений' в настройках канала.\n\n"
                    "Продолжить добавление канала? (да/нет)",
                    parse_mode="Markdown"
                )
                await state.update_data(
                    channel_id=channel_id,
                    channel_title=chat_info.title
                )
                await state.set_state(ChannelStates.confirming_channel_without_rights)
                return
                
        except Exception as e:
            logging.warning(f"Could not check bot permissions: {e}")
        
        # Всё хорошо, запрашиваем название
        await state.update_data(
            channel_id=channel_id,
            channel_title=chat_info.title
        )
        await state.set_state(ChannelStates.adding_channel_name)
        
        await message.answer(
            f"✅ *Канал найден!*\n\n"
            f"Название в Telegram: *{chat_info.title}*\n"
            f"ID: `{channel_id}`\n\n"
            f"Отправьте название для бота (или отправьте '-' чтобы использовать '{chat_info.title}'):",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await message.answer(
                "❌ *Канал не найден*\n\n"
                "Возможные причины:\n"
                "1️⃣ ID канала указан неверно\n"
                "2️⃣ Канал приватный и бот не добавлен\n"
                "3️⃣ Канал не существует\n\n"
                "Проверьте ID и попробуйте еще раз:",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ *Ошибка при проверке канала*\n\n"
                f"Детали: `{error_msg}`\n\n"
                f"Попробуйте еще раз или обратитесь к администратору.",
                parse_mode="Markdown"
            )


@router.message(ChannelStates.confirming_channel_without_rights, F.text)
async def process_confirm_channel(message: Message, state: FSMContext):
    """Подтверждение добавления канала без прав"""
    answer = message.text.strip().lower()
    
    if answer in ['да', 'yes', 'y', '+']:
        state_data = await state.get_data()
        channel_id = state_data.get('channel_id')
        channel_title = state_data.get('channel_title')
        
        await state.set_state(ChannelStates.adding_channel_name)
        
        await message.answer(
            f"📺 Канал: *{channel_title}*\n"
            f"ID: `{channel_id}`\n\n"
            f"Отправьте название для бота (или отправьте '-' чтобы использовать '{channel_title}'):",
            parse_mode="Markdown"
        )
    else:
        await state.clear()
        await message.answer("❌ Добавление канала отменено")


@router.message(ChannelStates.adding_channel_name, F.text)
async def process_channel_name(message: Message, state: FSMContext):
    """Обработка названия канала"""
    state_data = await state.get_data()
    channel_id = state_data.get('channel_id')
    channel_title = state_data.get('channel_title')
    
    # Определяем название
    if message.text.strip() == '-':
        channel_name = channel_title
    else:
        channel_name = message.text.strip()
    
    # Добавляем канал в БД
    success = await db.add_channel(channel_id, channel_name)
    
    if success:
        logging.info(f"Channel added: {channel_name} ({channel_id})")
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ *Канал успешно добавлен!*\n\n"
            f"📺 Название: {channel_name}\n"
            f"🆔 ID: `{channel_id}`",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при добавлении канала в базу данных")
    
    await state.clear()


@router.message(F.text == "🗑 Удалить канал")
async def btn_delete_channel(message: Message, state: FSMContext):
    """Начало удаления канала"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    channels = await db.get_all_channels()
    
    if not channels:
        await message.answer("❌ Нет каналов для удаления")
        return
    
    await state.set_state(ChannelStates.deleting_channel)
    
    # Создаем клавиатуру с каналами
    buttons = []
    for ch in channels:
        buttons.append([KeyboardButton(text=f"🗑 {ch['channel_name']}")])
    buttons.append([KeyboardButton(text="🔙 НАЗАД")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "🗑 *Удаление канала*\n\n"
        "Выберите канал для удаления:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(ChannelStates.deleting_channel, F.text.startswith("🗑 "))
async def process_delete_channel(message: Message, state: FSMContext):
    """Обработка удаления канала"""
    channel_name = message.text[2:].strip()  # Убираем "🗑 "
    
    # Ищем канал
    channels = await db.get_all_channels()
    selected_channel = None
    
    for ch in channels:
        if ch['channel_name'] == channel_name:
            selected_channel = ch
            break
    
    if not selected_channel:
        await message.answer("❌ Канал не найден")
        return
    
    # Удаляем канал
    success = await db.remove_channel(selected_channel['channel_id'])
    
    if success:
        logging.info(f"Channel deleted: {channel_name} ({selected_channel['channel_id']})")
        
        keyboard = main_menu_keyboard(True)
        
        await message.answer(
            f"✅ *Канал удален*\n\n"
            f"📺 {channel_name}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при удалении канала")
    
    await state.clear()
