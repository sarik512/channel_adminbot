"""
Обработчики загрузки контента для асинхронного бота
"""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import database_async as db
from main_async import (
    UploadStates, is_super_admin, is_admin_check, 
    parse_input, escape_markdown, bot
)
import logging

router = Router()


def channels_select_keyboard(channels: list) -> ReplyKeyboardMarkup:
    """Клавиатура выбора канала"""
    buttons = []
    for ch in channels:
        buttons.append([KeyboardButton(text=f"📺 {ch['channel_name']}")])
    buttons.append([KeyboardButton(text="🏠 Главное меню")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@router.message(F.text.in_(["📤 Загрузить", "📤 Загрузить контент"]))
async def btn_upload(message: Message, state: FSMContext):
    """Начало загрузки контента"""
    user_id = message.from_user.id
    
    if not await is_admin_check(user_id):
        return
    
    # Проверка доступа к каналам
    if not is_super_admin(user_id):
        channels = await db.get_admin_channels(user_id)
        if not channels:
            await message.answer(
                "❌ *Нет доступных каналов*\n\n"
                "Вы не назначены ни на один канал.\n"
                "Обратитесь к главному администратору.",
                parse_mode="Markdown"
            )
            return
    
    await state.set_state(UploadStates.waiting_info)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 НАЗАД")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "📤 *Загрузка контента*\n\n"
        "Отправьте информацию в формате:\n"
        "• `Название Сезон Серия` - для одной серии\n"
        "• `Название Сезон Серия1-Серия2` - для диапазона\n\n"
        "Примеры:\n"
        "• `Боевой континет 1 12`\n"
        "• `Боевой континет 1 1-12`",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(UploadStates.waiting_info, F.text)
async def process_upload_info(message: Message, state: FSMContext):
    """Обработка информации о видео"""
    user_id = message.from_user.id
    
    data = parse_input(message.text)
    if not data:
        await message.answer(
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
    
    # Сохраняем данные
    await state.update_data(data=data)
    
    # Получаем доступные каналы
    if is_super_admin(user_id):
        channels = await db.get_all_channels()
    else:
        channels = await db.get_admin_channels(user_id)
    
    if not channels:
        await message.answer("❌ Нет доступных каналов")
        await state.clear()
        return
    
    # Если канал один - автоматически выбираем
    if len(channels) == 1:
        await state.update_data(channel_id=channels[0]['channel_id'])
        await state.set_state(UploadStates.waiting_video)
        
        await message.answer(
            f"✅ Информация принята!\n"
            f"📺 Канал: *{channels[0]['channel_name']}*\n\n"
            "Теперь отправьте видео или документ.",
            parse_mode="Markdown"
        )
    else:
        # Показываем выбор каналов
        await state.set_state(UploadStates.selecting_channel)
        keyboard = channels_select_keyboard(channels)
        
        await message.answer(
            "✅ Информация принята!\n\n"
            "Выберите канал для публикации:",
            reply_markup=keyboard
        )


@router.message(UploadStates.selecting_channel, F.text.startswith("📺 "))
async def process_channel_selection(message: Message, state: FSMContext):
    """Обработка выбора канала"""
    user_id = message.from_user.id
    channel_name = message.text[2:].strip()  # Убираем "📺 "
    
    # Получаем доступные каналы
    if is_super_admin(user_id):
        channels = await db.get_all_channels()
    else:
        channels = await db.get_admin_channels(user_id)
    
    # Ищем выбранный канал
    selected_channel = None
    for ch in channels:
        if ch['channel_name'] == channel_name:
            selected_channel = ch
            break
    
    if not selected_channel:
        await message.answer("❌ Канал не найден")
        return
    
    await state.update_data(channel_id=selected_channel['channel_id'])
    await state.set_state(UploadStates.waiting_video)
    
    await message.answer(
        f"✅ Канал выбран: *{selected_channel['channel_name']}*\n\n"
        "Теперь отправьте видео или документ.",
        parse_mode="Markdown"
    )


@router.message(UploadStates.waiting_video, F.content_type.in_([ContentType.VIDEO, ContentType.DOCUMENT]))
async def process_video_upload(message: Message, state: FSMContext):
    """Обработка загрузки видео"""
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    state_data = await state.get_data()
    data = state_data.get('data')
    channel_id = state_data.get('channel_id')
    
    if not data or not channel_id:
        await message.answer("❌ Ошибка: данные не найдены. Начните заново.")
        await state.clear()
        return
    
    # Получаем информацию о канале
    channel = await db.get_channel(channel_id)
    if not channel:
        await message.answer("❌ Канал не найден")
        await state.clear()
        return
    
    # Формируем подпись
    template = await db.get_channel_template(channel_id)
    
    if template:
        # Используем шаблон
        caption = template['template_text']
        caption = caption.replace('{title}', data['title'])
        caption = caption.replace('{season}', str(data['season']))
        
        if data.get('is_range'):
            episode_str = f"{data['episode_start']}-{data['episode_end']}"
        else:
            episode_str = str(data['episode'])
        caption = caption.replace('{episode}', episode_str)
        caption = caption.replace('{tag}', data['tag'])
    else:
        # Стандартный формат
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
    
    try:
        # Отправляем в канал
        sent = None
        sent_file_id = None
        
        if message.content_type == ContentType.VIDEO:
            sent_file_id = message.video.file_id
            sent = await bot.send_video(channel_id, sent_file_id, caption=caption)
        else:
            sent_file_id = message.document.file_id
            sent = await bot.send_document(channel_id, sent_file_id, caption=caption)
        
        message_id = str(sent.message_id) if sent else None
        
        # Логируем в статистику
        episode_for_log = data.get('episode') or data.get('episode_start', 0)
        
        await db.log_upload(
            user_id,
            channel_id,
            data['title'],
            int(data['season']),
            int(episode_for_log),
            file_id=sent_file_id,
            message_id=message_id
        )
        
        # Формируем строку для логирования
        if data.get('is_range'):
            episode_log = f"S{data['season']}E{data['episode_start']}-{data['episode_end']}"
        else:
            episode_log = f"S{data['season']}E{data['episode']}"
        
        logging.info(
            f"Published | {data['title']} | {episode_log} | "
            f"Channel: {channel['channel_name']} | Admin: {user_id} | msg_id={message_id}"
        )
        
        await message.answer(
            f"✅ *Успешно опубликовано!*\n\n"
            f"📺 Канал: {channel['channel_name']}\n"
            f"🎬 {data['title']}\n"
            f"📺 Сезон {data['season']}, {episode_text}",
            parse_mode="Markdown"
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error publishing to channel {channel_id}: {error_msg}")
        
        if "bot was blocked" in error_msg.lower():
            await message.answer(
                "❌ *Ошибка публикации*\n\n"
                "Бот заблокирован в канале или не имеет прав на публикацию.\n"
                "Проверьте права бота в настройках канала.",
                parse_mode="Markdown"
            )
        elif "chat not found" in error_msg.lower():
            await message.answer(
                "❌ *Ошибка публикации*\n\n"
                "Канал не найден. Возможно, бот был удален из канала.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ *Ошибка публикации*\n\n"
                f"Детали: `{error_msg}`",
                parse_mode="Markdown"
            )
        
        await state.clear()
