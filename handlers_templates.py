"""
Обработчики управления шаблонами для асинхронного бота
"""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

import database_async as db
from main_async import (
    TemplateStates, is_super_admin, is_admin_check,
    escape_markdown, main_menu_keyboard
)
import logging

router = Router()


def templates_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню управления шаблонами"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить шаблон"), KeyboardButton(text="📋 Список шаблонов")],
            [KeyboardButton(text="🔗 Прикрепить к каналу")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def template_actions_keyboard() -> ReplyKeyboardMarkup:
    """Меню действий с шаблоном"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👁 Просмотр"), KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="🗑 Удалить шаблон")],
            [KeyboardButton(text="🔙 К списку шаблонов"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "📝 Шаблоны")
async def btn_templates(message: Message):
    """Меню управления шаблонами"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    templates = await db.get_all_templates()
    response = "📝 *Управление шаблонами*\n\n"
    
    if not templates:
        response += "❌ Нет созданных шаблонов\n\n"
        response += "Используйте кнопку '➕ Добавить шаблон' для создания."
    else:
        response += "*Список шаблонов:*\n\n"
        for tmpl in templates:
            response += f"• {tmpl['name']}\n"
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=templates_menu_keyboard()
    )


@router.message(F.text == "➕ Добавить шаблон")
async def btn_add_template(message: Message, state: FSMContext):
    """Начало добавления шаблона"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    await state.set_state(TemplateStates.adding_template_name)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 НАЗАД")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "📝 *Создание шаблона*\n\n"
        "Отправьте название шаблона:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(TemplateStates.adding_template_name, F.text)
async def process_template_name(message: Message, state: FSMContext):
    """Обработка названия шаблона"""
    template_name = message.text.strip()
    
    # Проверяем, не существует ли уже
    existing = await db.get_template_by_name(template_name)
    if existing:
        await message.answer(
            f"⚠️ Шаблон с таким названием уже существует!\n\n"
            f"Попробуйте другое название:"
        )
        return
    
    await state.update_data(template_name=template_name)
    await state.set_state(TemplateStates.adding_template_text)
    
    await message.answer(
        f"📝 Название: *{template_name}*\n\n"
        f"Теперь отправьте текст шаблона.\n\n"
        f"Доступные переменные:\n"
        f"• `{{title}}` - название\n"
        f"• `{{season}}` - сезон\n"
        f"• `{{episode}}` - серия\n"
        f"• `{{tag}}` - тег\n\n"
        f"Пример:\n"
        f"`🎬 {{title}}`\n"
        f"`📺 Сезон {{season}}, Серия {{episode}}`\n"
        f"`{{tag}}`",
        parse_mode="Markdown"
    )


@router.message(TemplateStates.adding_template_text, F.text)
async def process_template_text(message: Message, state: FSMContext):
    """Обработка текста шаблона"""
    state_data = await state.get_data()
    template_name = state_data.get('template_name')
    template_text = message.text
    
    # Добавляем шаблон
    template_id = await db.add_template(template_name, template_text)
    
    if template_id:
        logging.info(f"Template created: {template_name} (ID: {template_id})")
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ *Шаблон создан!*\n\n"
            f"📝 Название: {template_name}\n"
            f"🆔 ID: {template_id}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при создании шаблона")
    
    await state.clear()


@router.message(F.text == "📋 Список шаблонов")
async def btn_templates_list(message: Message, state: FSMContext):
    """Список шаблонов для управления"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    templates = await db.get_all_templates()
    
    if not templates:
        await message.answer("❌ Нет шаблонов")
        return
    
    await state.set_state(TemplateStates.selecting_template)
    
    # Создаем клавиатуру с шаблонами
    buttons = []
    for tmpl in templates:
        buttons.append([KeyboardButton(text=f"📝 {tmpl['name']}")])
    buttons.append([
        KeyboardButton(text="🔙 К шаблонам"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "📋 *Выберите шаблон:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(TemplateStates.selecting_template, F.text.startswith("📝 "))
async def process_select_template(message: Message, state: FSMContext):
    """Обработка выбора шаблона"""
    template_name = message.text[2:].strip()  # Убираем "📝 "
    
    template = await db.get_template_by_name(template_name)
    
    if not template:
        await message.answer("❌ Шаблон не найден")
        return
    
    await state.update_data(selected_template_id=template['id'])
    await state.set_state(TemplateStates.template_actions)
    
    await message.answer(
        f"📝 *Шаблон: {template['name']}*\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=template_actions_keyboard()
    )


@router.message(TemplateStates.template_actions, F.text == "👁 Просмотр")
async def btn_view_template(message: Message, state: FSMContext):
    """Просмотр шаблона"""
    state_data = await state.get_data()
    template_id = state_data.get('selected_template_id')
    
    template = await db.get_template(template_id)
    
    if not template:
        await message.answer("❌ Шаблон не найден")
        await state.clear()
        return
    
    await message.answer(
        f"📝 *{template['name']}*\n\n"
        f"Текст шаблона:\n"
        f"```\n{template['template_text']}\n```",
        parse_mode="Markdown"
    )


@router.message(TemplateStates.template_actions, F.text == "🗑 Удалить шаблон")
async def btn_delete_template(message: Message, state: FSMContext):
    """Удаление шаблона"""
    state_data = await state.get_data()
    template_id = state_data.get('selected_template_id')
    
    template = await db.get_template(template_id)
    
    if not template:
        await message.answer("❌ Шаблон не найден")
        await state.clear()
        return
    
    success = await db.remove_template(template_id)
    
    if success:
        logging.info(f"Template deleted: {template['name']} (ID: {template_id})")
        
        keyboard = main_menu_keyboard(True)
        
        await message.answer(
            f"✅ *Шаблон удален*\n\n"
            f"📝 {template['name']}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при удалении шаблона")
    
    await state.clear()


@router.message(F.text == "🔗 Прикрепить к каналу")
async def btn_assign_template(message: Message, state: FSMContext):
    """Начало прикрепления шаблона к каналу"""
    user_id = message.from_user.id
    
    if not is_super_admin(user_id):
        await message.answer("⛔ Только для супер-админа")
        return
    
    templates = await db.get_all_templates()
    
    if not templates:
        await message.answer("❌ Нет шаблонов. Создайте шаблон сначала.")
        return
    
    await state.set_state(TemplateStates.selecting_template_for_channel)
    
    # Создаем клавиатуру с шаблонами
    buttons = []
    for tmpl in templates:
        buttons.append([KeyboardButton(text=f"📝 {tmpl['name']}")])
    buttons.append([KeyboardButton(text="🔙 НАЗАД")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "📝 *Выберите шаблон для прикрепления:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(TemplateStates.selecting_template_for_channel, F.text.startswith("📝 "))
async def process_select_template_for_channel(message: Message, state: FSMContext):
    """Обработка выбора шаблона для прикрепления"""
    template_name = message.text[2:].strip()
    
    template = await db.get_template_by_name(template_name)
    
    if not template:
        await message.answer("❌ Шаблон не найден")
        return
    
    await state.update_data(selected_template_id=template['id'])
    
    # Получаем все каналы
    channels = await db.get_all_channels()
    
    if not channels:
        await message.answer("❌ Нет каналов")
        await state.clear()
        return
    
    await state.set_state(TemplateStates.assigning_template_to_channel)
    
    # Создаем клавиатуру с каналами
    buttons = []
    for ch in channels:
        # Проверяем, прикреплен ли уже шаблон к этому каналу
        ch_template = await db.get_channel_template(ch['channel_id'])
        if ch_template and ch_template['id'] == template['id']:
            buttons.append([KeyboardButton(text=f"✅ {ch['channel_name']}")])
        else:
            buttons.append([KeyboardButton(text=f"📺 {ch['channel_name']}")])
    
    buttons.append([
        KeyboardButton(text="🔙 К шаблонам"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        f"📝 Шаблон: *{template['name']}*\n\n"
        f"Выберите канал для прикрепления:\n"
        f"✅ - уже прикреплен этот шаблон\n"
        f"📺 - другой шаблон или нет шаблона",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(TemplateStates.assigning_template_to_channel, F.text.regexp(r"^[✅📺] "))
async def process_assign_template_to_channel(message: Message, state: FSMContext):
    """Обработка прикрепления шаблона к каналу"""
    state_data = await state.get_data()
    template_id = state_data.get('selected_template_id')
    
    channel_name = message.text[2:].strip()  # Убираем "✅ " или "📺 "
    
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
    
    # Прикрепляем шаблон
    success = await db.assign_template_to_channel(selected_channel['channel_id'], template_id)
    
    if success:
        template = await db.get_template(template_id)
        logging.info(f"Template '{template['name']}' assigned to channel '{channel_name}'")
        
        # Обновляем клавиатуру
        buttons = []
        for ch in channels:
            ch_template = await db.get_channel_template(ch['channel_id'])
            if ch_template and ch_template['id'] == template_id:
                buttons.append([KeyboardButton(text=f"✅ {ch['channel_name']}")])
            else:
                buttons.append([KeyboardButton(text=f"📺 {ch['channel_name']}")])
        
        buttons.append([
            KeyboardButton(text="🔙 К шаблонам"),
            KeyboardButton(text="🏠 Главное меню")
        ])
        
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        
        await message.answer(
            f"✅ Шаблон прикреплен к каналу *{channel_name}*",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Ошибка при прикреплении шаблона")


@router.message(TemplateStates.selecting_template, F.text == "🔙 К шаблонам")
@router.message(TemplateStates.assigning_template_to_channel, F.text == "🔙 К шаблонам")
async def btn_back_to_templates(message: Message, state: FSMContext):
    """Возврат к меню шаблонов"""
    await state.clear()
    
    templates = await db.get_all_templates()
    response = "📝 *Управление шаблонами*\n\n"
    
    if not templates:
        response += "❌ Нет созданных шаблонов"
    else:
        response += "*Список шаблонов:*\n\n"
        for tmpl in templates:
            response += f"• {tmpl['name']}\n"
    
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=templates_menu_keyboard()
    )


@router.message(TemplateStates.template_actions, F.text == "🔙 К списку шаблонов")
async def btn_back_to_templates_list(message: Message, state: FSMContext):
    """Возврат к списку шаблонов"""
    templates = await db.get_all_templates()
    
    if not templates:
        await message.answer("❌ Нет шаблонов")
        await state.clear()
        return
    
    await state.set_state(TemplateStates.selecting_template)
    
    buttons = []
    for tmpl in templates:
        buttons.append([KeyboardButton(text=f"📝 {tmpl['name']}")])
    buttons.append([
        KeyboardButton(text="🔙 К шаблонам"),
        KeyboardButton(text="🏠 Главное меню")
    ])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    await message.answer(
        "📋 *Выберите шаблон:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
