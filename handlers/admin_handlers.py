"""
Обработчики для админ-панели
"""
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import dp
from utils.admin_broadcast import get_broadcast_manager
from utils.decorators import if_admin
from utils.state import States
from utils.ui_constants import ButtonFactory
from utils.admin_user_manager import get_user_manager
from utils.log import create_logger

logger = create_logger(__name__)


async def show_user_search_page(msg_or_call: types.Message | types.CallbackQuery, users, page: int, state: FSMContext):
    """
    Показать страницу результатов поиска пользователей
    
    Args:
        msg_or_call: Message или CallbackQuery
        users: Список пользователей
        page: Номер страницы (начиная с 0)
        state: FSM контекст
    """
    USERS_PER_PAGE = 10
    total_users = len(users)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    
    # Вычисляем диапазон пользователей для текущей страницы
    start_idx = page * USERS_PER_PAGE
    end_idx = min(start_idx + USERS_PER_PAGE, total_users)
    page_users = users[start_idx:end_idx]
    
    # Формируем текст
    text = f"🔍 <b>Найдено пользователей: {total_users}</b>\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    text += "Выберите пользователя:"
    
    # Создаем кнопки для пользователей на текущей странице
    btns = []
    for i, user in enumerate(page_users, start=start_idx + 1):
        username = f"@{user['username']}" if user['username'] else "без username"
        btn_text = f"{i}. {username} | {user['group_id']} | {user['missed_hours'] or 0}ч"
        btns.append([types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"user_profile:{user['user_id']}"
        )])
    
    # Добавляем кнопки навигации
    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"user_search_page:{page - 1}"
        ))
    
    nav_btns.append(types.InlineKeyboardButton(
        text=f"📄 {page + 1}/{total_pages}",
        callback_data="noop"
    ))
    
    if page < total_pages - 1:
        nav_btns.append(types.InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"user_search_page:{page + 1}"
        ))
    
    if nav_btns:
        btns.append(nav_btns)
    
    btns.append([ButtonFactory.back("menu:users_management")])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    # Отправляем или редактируем сообщение
    if isinstance(msg_or_call, types.Message):
        await msg_or_call.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await msg_or_call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")



logger = create_logger(__name__)


# ============================================================================
# ОБРАБОТЧИКИ ДЛЯ РАССЫЛОК
# ============================================================================

@dp.message(States.broadcast_message)
@if_admin('msg')
async def broadcast_message_handler(msg: types.Message, state: FSMContext):
    """Обработка текста рассылки"""
    state_data = await state.get_data()
    filter_type = state_data.get('filter_type', 'all')
    filter_params = state_data.get('filter_params', {})
    
    # Сохраняем текст сообщения
    await state.update_data(message_text=msg.html_text)
    
    # Показываем предпросмотр
    broadcast_manager = get_broadcast_manager()
    preview_text = broadcast_manager.format_broadcast_preview(
        filter_type, filter_params, msg.html_text
    )
    
    btns = [
        [types.InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:confirm")],
        [types.InlineKeyboardButton(text="✏️ Изменить текст", callback_data="broadcast:edit_text")],
        [types.InlineKeyboardButton(text="🔙 Изменить фильтр", callback_data="menu:broadcast_create")],
        [ButtonFactory.cancel("menu:broadcast_main")]
    ]
    
    await msg.answer(preview_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@dp.message(States.broadcast_filter_groups)
@if_admin('msg')
async def broadcast_filter_groups_handler(msg: types.Message, state: FSMContext):
    """Обработка выбора групп для рассылки"""
    from config import groups
    
    # Парсим группы из сообщения
    input_groups = msg.text.replace(',', ' ').split()
    valid_groups = [g for g in input_groups if g in groups]
    
    if not valid_groups:
        await msg.answer(
            "❌ Не найдено ни одной валидной группы.\n\n"
            "Попробуйте еще раз или отмените действие.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
        )
        return
    
    # Сохраняем параметры фильтра
    await state.update_data(
        filter_type='by_group',
        filter_params={'groups': valid_groups}
    )
    
    # Переходим к вводу текста
    await state.set_state(States.broadcast_message)
    
    await msg.answer(
        f"✅ Выбрано групп: {len(valid_groups)}\n\n"
        f"Группы: {', '.join(valid_groups)}\n\n"
        "📝 Теперь отправьте текст рассылки:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_main")]])
    )


@dp.message(States.broadcast_filter_activity_days)
@if_admin('msg')
async def broadcast_filter_activity_handler(msg: types.Message, state: FSMContext):
    """Обработка фильтра по активности"""
    try:
        days = int(msg.text)
        if days < 1 or days > 365:
            raise ValueError
    except ValueError:
        await msg.answer(
            "❌ Введите корректное число дней (от 1 до 365)",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
        )
        return
    
    await state.update_data(
        filter_type='by_activity',
        filter_params={'days': days}
    )
    
    await state.set_state(States.broadcast_message)
    
    await msg.answer(
        f"✅ Фильтр установлен: активные за последние {days} дней\n\n"
        "📝 Теперь отправьте текст рассылки:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_main")]])
    )


@dp.message(States.broadcast_filter_hours_min)
@if_admin('msg')
async def broadcast_filter_hours_min_handler(msg: types.Message, state: FSMContext):
    """Обработка минимального количества пропусков"""
    try:
        min_hours = int(msg.text)
        if min_hours < 0:
            raise ValueError
    except ValueError:
        await msg.answer(
            "❌ Введите корректное число (от 0)",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
        )
        return
    
    await state.update_data(min_hours=min_hours)
    await state.set_state(States.broadcast_filter_hours_max)
    
    await msg.answer(
        f"✅ Минимум: {min_hours}ч\n\n"
        "Теперь введите максимальное количество пропущенных часов:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
    )


@dp.message(States.broadcast_filter_hours_max)
@if_admin('msg')
async def broadcast_filter_hours_max_handler(msg: types.Message, state: FSMContext):
    """Обработка максимального количества пропусков"""
    try:
        max_hours = int(msg.text)
        if max_hours < 0:
            raise ValueError
    except ValueError:
        await msg.answer(
            "❌ Введите корректное число (от 0)",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
        )
        return
    
    state_data = await state.get_data()
    min_hours = state_data.get('min_hours', 0)
    
    if max_hours < min_hours:
        await msg.answer(
            f"❌ Максимум ({max_hours}) не может быть меньше минимума ({min_hours})",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_create")]])
        )
        return
    
    await state.update_data(
        filter_type='by_hours',
        filter_params={'min_hours': min_hours, 'max_hours': max_hours}
    )
    
    await state.set_state(States.broadcast_message)
    
    await msg.answer(
        f"✅ Фильтр установлен: от {min_hours}ч до {max_hours}ч\n\n"
        "📝 Теперь отправьте текст рассылки:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:broadcast_main")]])
    )


# ============================================================================
# ОБРАБОТЧИКИ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ
# ============================================================================

@dp.message(States.admin_search_user)
@if_admin('msg')
async def admin_search_user_handler(msg: types.Message, state: FSMContext):
    """Обработка поиска пользователя"""
    await state.clear()
    
    user_manager = get_user_manager()
    users = user_manager.search_users(msg.text)
    
    if not users:
        await msg.answer(
            "❌ Пользователи не найдены\n\n"
            "Попробуйте другой запрос",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )
        return
    
    if len(users) == 1:
        # Показываем профиль сразу
        user = users[0]
        profile = user_manager.get_user_profile(user['user_id'])
        
        if profile:
            text = user_manager.format_user_profile(profile)
            
            btns = [
                [types.InlineKeyboardButton(text="📊 История активности", callback_data=f"user_activity:{user['user_id']}")],
                [types.InlineKeyboardButton(text="📈 История пропусков", callback_data=f"user_hours_history:{user['user_id']}")],
                [types.InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data=f"user_send_msg:{user['user_id']}")],
                [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data=f"user_change_group:{user['user_id']}")],
                [types.InlineKeyboardButton(text="🔄 Сбросить пропуски", callback_data=f"user_reset_hours:{user['user_id']}")],
                [types.InlineKeyboardButton(
                    text="🚫 Заблокировать" if not profile['is_blocked'] else "✅ Разблокировать",
                    callback_data=f"user_toggle_block:{user['user_id']}"
                )],
                [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"user_delete:{user['user_id']}")],
                [ButtonFactory.back("menu:users_management")]
            ]
            
            await msg.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    else:
        # Сохраняем список пользователей в state для пагинации
        users_data = [{'user_id': u['user_id'], 'username': u['username'], 
                       'group_id': u['group_id'], 'missed_hours': u['missed_hours']} 
                      for u in users]
        await state.update_data(search_results=users_data)
        
        # Показываем первую страницу
        await show_user_search_page(msg, users, page=0, state=state)


@dp.message(States.admin_user_send_message)
@if_admin('msg')
async def admin_user_send_message_handler(msg: types.Message, state: FSMContext):
    """Отправка личного сообщения пользователю"""
    state_data = await state.get_data()
    target_user_id = state_data.get('target_user_id')
    
    await state.clear()
    
    if not target_user_id:
        await msg.answer("❌ Ошибка: пользователь не найден")
        return
    
    user_manager = get_user_manager()
    success = await user_manager.send_personal_message(target_user_id, msg.html_text, msg.from_user.id)
    
    if success:
        await msg.answer(
            "✅ Сообщение отправлено",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )
    else:
        await msg.answer(
            "❌ Не удалось отправить сообщение",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )


@dp.message(States.admin_user_change_group)
@if_admin('msg')
async def admin_user_change_group_handler(msg: types.Message, state: FSMContext):
    """Изменение группы пользователя"""
    from config import groups
    
    state_data = await state.get_data()
    target_user_id = state_data.get('target_user_id')
    is_secondary = state_data.get('is_secondary', False)
    
    await state.clear()
    
    if not target_user_id:
        await msg.answer("❌ Ошибка: пользователь не найден")
        return
    
    new_group = msg.text.strip()
    
    if new_group not in groups:
        await msg.answer(
            f"❌ Группа {new_group} не найдена в списке доступных групп",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )
        return
    
    user_manager = get_user_manager()
    success = user_manager.change_user_group(target_user_id, new_group, is_secondary, msg.from_user.id)
    
    if success:
        group_type = "дополнительная" if is_secondary else "основная"
        await msg.answer(
            f"✅ {group_type.capitalize()} группа изменена на {new_group}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="👤 К профилю", callback_data=f"user_profile:{target_user_id}")
            ]])
        )
    else:
        await msg.answer(
            "❌ Не удалось изменить группу",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )


@dp.message(States.admin_cleanup_days)
@if_admin('msg')
async def admin_cleanup_days_handler(msg: types.Message, state: FSMContext):
    """Очистка неактивных пользователей"""
    await state.clear()
    
    try:
        days = int(msg.text)
        if days < 1:
            raise ValueError
    except ValueError:
        await msg.answer(
            "❌ Введите корректное число дней (от 1)",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )
        return
    
    # Запрашиваем подтверждение
    await state.update_data(cleanup_days=days)
    
    text = f"⚠️ <b>ПОДТВЕРЖДЕНИЕ</b>\n\n"
    text += f"Вы уверены, что хотите удалить всех пользователей,\n"
    text += f"которые не были активны более {days} дней?\n\n"
    text += "Это действие необратимо!"
    
    btns = [
        [
            types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"cleanup_confirm:{days}"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="menu:users_management")
        ]
    ]
    
    await msg.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@dp.message(States.admin_block_reason)
@if_admin('msg')
async def admin_block_reason_handler(msg: types.Message, state: FSMContext):
    """Обработка причины блокировки"""
    state_data = await state.get_data()
    target_user_id = state_data.get('target_user_id')
    
    logger.info(f"Block reason received for user {target_user_id}: {msg.text}")
    
    await state.clear()
    
    if not target_user_id:
        logger.warning("No target_user_id in state")
        await msg.answer("❌ Ошибка: пользователь не найден")
        return
    
    user_manager = get_user_manager()
    success = user_manager.block_user(target_user_id, msg.from_user.id, msg.text)
    
    logger.info(f"Block user {target_user_id} result: {success}")
    
    if success:
        await msg.answer(
            "✅ Пользователь заблокирован",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )
    else:
        await msg.answer(
            "❌ Не удалось заблокировать пользователя",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:users_management")]])
        )


# ============================================================================
# ОБРАБОТЧИК ПАГИНАЦИИ ПОИСКА ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

@dp.callback_query(lambda c: c.data.startswith("user_search_page:"))
@if_admin('call')
async def user_search_page_handler(call: types.CallbackQuery, state: FSMContext):
    """Обработка переключения страниц в результатах поиска"""
    page = int(call.data.split(":")[1])
    
    logger.info(f"Page switch requested: page={page}")
    
    # Получаем сохраненные результаты поиска
    state_data = await state.get_data()
    users_data = state_data.get('search_results', [])
    
    logger.info(f"State data: {len(users_data)} users found in state")
    
    if not users_data:
        logger.warning("No search results in state")
        await call.answer("❌ Результаты поиска устарели. Выполните поиск заново.", show_alert=True)
        return
    
    # Показываем нужную страницу
    logger.info(f"Showing page {page} with {len(users_data)} users")
    await show_user_search_page(call, users_data, page, state)
    await call.answer()
