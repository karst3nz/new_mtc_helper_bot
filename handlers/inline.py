import aiogram.exceptions
from config import dp, bot, types, F, FSMContext
from utils.log import create_logger
from typing import Callable
from utils.menus import *
from utils.db import DB
from utils.decorators import if_admin
from utils.calendar_keyboard import create_calendar, process_calendar_callback
from utils.callback_data import CallbackData
from utils.ui_constants import ButtonFactory
from utils.state import States
logger = create_logger(__name__)


@dp.callback_query(F.data.startswith("ad_"))
@if_admin("call")
async def ad1(call: types.CallbackQuery, state: FSMContext):
    import re
    import asyncio

    async def send(user_id: int, msg2forward: types.Message, max_retries: int = 20):
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # await msg2forward.forward(chat_id=user_id)
                await bot.send_message(chat_id=user_id, text=msg2forward.html_text, parse_mode="HTML")
                logger.info(f"Рассылка успешно отправлена к user_id={user_id}")
                return True
            except aiogram.exceptions.TelegramBadRequest as e:
                # Неудачная попытка повторной отправки, не связанная с лимитом
                logger.info(f"Рассылка не была отправлена к user_id={user_id}; e={str(e)} (BadRequest)")
                return False
            except aiogram.exceptions.TelegramRetryAfter as e:
                # aiogram >= 3.0: TelegramRetryAfter содержит .retry_after
                delay = getattr(e, "retry_after", None)
                if delay is None:
                    # Попробуем найти время ожидания через regex из текста ошибки
                    m = re.search(r"Retry in (\d+) seconds", str(e))
                    if m:
                        delay = int(m.group(1))
                    else:
                        delay = 30  # fallback: 30 сек
                logger.warning(f"Flood control (RetryAfter): ждем {delay} сек и повторим отправку user_id={user_id}")
                await asyncio.sleep(delay)
                retry_count += 1
            except Exception as e:
                # Дополнительно: ловим Too Many Requests через текст ошибки (если сработал raw exception)
                text = str(e)
                if isinstance(e, aiogram.exceptions.TelegramAPIError) and "Too Many Requests" in text:
                    m = re.search(r"Retry in (\d+) seconds", text)
                    delay = int(m.group(1)) if m else 30
                    logger.warning(f"Flood control (APIError): ждем {delay} сек и повторим попытку user_id={user_id}")
                    await asyncio.sleep(delay)
                    retry_count += 1
                    continue
                logger.info(f"Рассылка не была отправлена к user_id={user_id}; e={text}")
                return False
        logger.info(f"Рассылка не удалась (max retries) к user_id={user_id}")
        return False

    action = call.data.split("_")[1]
    state_data = await state.get_data()
    await state.clear()

    # Безопасно получаем сообщения из state_data
    msg2forward: types.Message = state_data.get("msg2forward")
    msg2delete = state_data.get("msg2delete")

    if action == "confirm":
        if msg2forward is None:
            await call.message.answer("❌ Не найдено сообщение для рассылки. Попробуйте начать заново.")
            return
        tasks = []
        db = DB()
        user_ids = db.get_all("user_id", db.users_table)
        for user_id in user_ids:
            tasks.append(send(user_id, msg2forward))
        # Вынесем gather из цикла, чтобы не было ошибки reuse coroutine
        r = await asyncio.gather(*tasks)
        success = r.count(True)
        errors = r.count(False)    
        await call.message.answer(text=f"Итоги рассылки:\n✅ success={success}\n❌ errors={errors}")    
    else:
        await call.message.answer("❌ Отменено")
    if msg2delete is not None:
        try:
            await bot.delete_messages(chat_id=call.from_user.id, message_ids=msg2delete)
        except Exception as e:
            logger.warning(f"Ошибка при удалении сообщений: {e}")

@dp.callback_query(F.data == "delete_msg")
async def delete_msg(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer()


@dp.callback_query(F.data == "check_pin_rights")
async def check_pin_rights(call: types.CallbackQuery):
    await call.answer()
    try: 
        await call.message.pin(disable_notification=True)
        await call.message.unpin()
        await call.message.edit_text(text='✅ Права выданы верно!', reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.close()]]))
    except Exception as e:
        from utils.log import create_logger
        logger = create_logger(__name__)
        logger.error(f"Permission check failed: {e}")
        await call.message.reply("❌ Проверка не удалась, проверьте права бота!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.close()]]))


@dp.callback_query(F.data.startswith("calendar:"))
async def calendar_handler(call: types.CallbackQuery, state: FSMContext):
    """Обработчик календаря"""
    result = process_calendar_callback(call.data)
    
    if result["action"] == "ignore":
        await call.answer()
        return
    
    elif result["action"] == "change_month":
        # Обновляем календарь на новый месяц
        new_calendar = create_calendar(result["year"], result["month"])
        try:
            await call.message.edit_reply_markup(reply_markup=new_calendar)
        except aiogram.exceptions.TelegramBadRequest:
            pass
        await call.answer()
    
    elif result["action"] == "select":
        # Пользователь выбрал дату
        date_str = result["date_str"]
        
        # Используем функцию rasp из menus.py для получения полного расписания
        from utils.menus import rasp as get_rasp
        
        try:
            # Получаем расписание через функцию menus.rasp
            text, btns = await get_rasp(call.from_user.id, date=date_str, _get_new=False, show_lessons_time=False)
            
            await call.message.edit_text(text, reply_markup=btns, parse_mode="HTML", disable_web_page_preview=True)
            await call.answer()
        
        except Exception as e:
            logger.error(f"Error loading schedule from calendar: {e}")
            await call.message.edit_text(
                f"❌ Не удалось загрузить расписание\n\n💡 Попробуйте позже",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="◀️ Назад к календарю", callback_data="menu:show_calendar")
                ]])
            )
            await call.answer()


# ============================================================================
# НОВЫЕ CALLBACK ОБРАБОТЧИКИ ДЛЯ АДМИН-ПАНЕЛИ
# ============================================================================

# Рассылки
@dp.callback_query(F.data.startswith("broadcast_filter:"))
@if_admin("call")
async def broadcast_filter_handler(call: types.CallbackQuery, state: FSMContext):
    """Обработка выбора фильтра для рассылки"""
    filter_type = call.data.split(":")[1]
    
    logger.info(f"Processing broadcast filter: {filter_type}")
    
    try:
        if filter_type == "all":
            await state.update_data(filter_type='all', filter_params={})
            await state.set_state(States.broadcast_message)
            
            text = "📢 <b>РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ</b>\n\n📝 Отправьте текст рассылки:"
            btns = [[ButtonFactory.cancel("menu:broadcast_main")]]
            
            await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        
        elif filter_type == "by_group":
            await state.set_state(States.broadcast_filter_groups)
            
            from config import groups
            text = "📚 <b>РАССЫЛКА ПО ГРУППАМ</b>\n\n"
            text += "Отправьте номера групп через пробел или запятую.\n\n"
            text += f"<b>Доступные группы:</b>\n{', '.join(groups[:20])}"
            if len(groups) > 20:
                text += f"\n... и еще {len(groups) - 20}"
            
            btns = [[ButtonFactory.cancel("menu:broadcast_create")]]
            await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        
        elif filter_type == "by_activity":
            await state.set_state(States.broadcast_filter_activity_days)
            
            text = "⚡ <b>РАССЫЛКА ПО АКТИВНОСТИ</b>\n\n"
            text += "Отправьте количество дней (например: 7)\n\n"
            text += "Рассылка будет отправлена пользователям,\nкоторые были активны за последние N дней."
            
            btns = [[ButtonFactory.cancel("menu:broadcast_create")]]
            await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        
        elif filter_type == "by_hours":
            await state.set_state(States.broadcast_filter_hours_min)
            
            text = "⏰ <b>РАССЫЛКА ПО ПРОПУСКАМ</b>\n\n"
            text += "Отправьте минимальное количество пропущенных часов:"
            
            btns = [[ButtonFactory.cancel("menu:broadcast_create")]]
            await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        
        elif filter_type == "test":
            await state.update_data(filter_type='test', filter_params={})
            await state.set_state(States.broadcast_message)
            
            text = "🧪 <b>ТЕСТОВАЯ РАССЫЛКА</b>\n\n"
            text += "Сообщение будет отправлено только вам.\n\n"
            text += "📝 Отправьте текст рассылки:"
            
            btns = [[ButtonFactory.cancel("menu:broadcast_main")]]
            await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        
        await call.answer()
        logger.info(f"Broadcast filter {filter_type} processed successfully")
        
    except Exception as e:
        logger.error(f"Error in broadcast_filter_handler: {e}", exc_info=True)
        await call.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@dp.callback_query(F.data == "broadcast:confirm")
@if_admin("call")
async def broadcast_confirm_handler(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    state_data = await state.get_data()
    message_text = state_data.get('message_text')
    filter_type = state_data.get('filter_type')
    filter_params = state_data.get('filter_params', {})
    
    await state.clear()
    
    from utils.admin_broadcast import get_broadcast_manager
    
    broadcast_manager = get_broadcast_manager()
    
    # Создаем рассылку
    broadcast_id = broadcast_manager.create_broadcast(
        admin_id=call.from_user.id,
        message_text=message_text,
        filter_type=filter_type,
        filter_params=filter_params
    )
    
    if not broadcast_id:
        await call.message.edit_text(
            "❌ Не удалось создать рассылку",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:broadcast_main")]])
        )
        await call.answer()
        return
    
    # Отправляем начальное сообщение о прогрессе
    progress_msg = await call.message.edit_text(
        "📤 <b>Рассылка запущена...</b>\n\nИнициализация...",
        parse_mode="HTML"
    )
    
    # Функция обновления прогресса
    async def update_progress(current, total, success, errors):
        percent = int((current / total) * 100) if total > 0 else 0
        bar_length = 10
        filled = int((percent / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        text = f"📤 <b>Рассылка в процессе...</b>\n\n"
        text += f"Прогресс: [{bar}] {percent}%\n"
        text += f"Отправлено: {current}/{total}\n"
        text += f"✅ Успешно: {success}\n"
        text += f"❌ Ошибок: {errors}"
        
        try:
            await progress_msg.edit_text(text, parse_mode="HTML")
        except:
            pass
    
    # Запускаем рассылку
    stats = await broadcast_manager.send_broadcast(broadcast_id, update_progress)
    
    # Финальное сообщение
    text = f"✅ <b>Рассылка завершена!</b>\n\n"
    text += f"<b>Всего:</b> {stats['success'] + stats['errors']}\n"
    text += f"<b>Успешно:</b> {stats['success']}\n"
    text += f"<b>Ошибок:</b> {stats['errors']}"
    
    btns = [[ButtonFactory.back("menu:broadcast_main")]]
    
    await progress_msg.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


# Управление пользователями
@dp.callback_query(F.data.startswith("user_profile:"))
@if_admin("call")
async def user_profile_handler(call: types.CallbackQuery, state: FSMContext):
    """Показать профиль пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    profile = user_manager.get_user_profile(user_id)
    
    if not profile:
        await call.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    text = user_manager.format_user_profile(profile)
    
    btns = [
        [types.InlineKeyboardButton(text="📊 История активности", callback_data=f"user_activity:{user_id}")],
        [types.InlineKeyboardButton(text="📈 История пропусков", callback_data=f"user_hours_history:{user_id}")],
        [types.InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data=f"user_send_msg:{user_id}")],
        [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data=f"user_change_group:{user_id}")],
        [types.InlineKeyboardButton(text="🔄 Сбросить пропуски", callback_data=f"user_reset_hours:{user_id}")],
        [types.InlineKeyboardButton(
            text="🚫 Заблокировать" if not profile['is_blocked'] else "✅ Разблокировать",
            callback_data=f"user_toggle_block:{user_id}"
        )],
        [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"user_delete:{user_id}")],
        [ButtonFactory.back("menu:users_management")]
    ]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_send_msg:"))
@if_admin("call")
async def user_send_msg_handler(call: types.CallbackQuery, state: FSMContext):
    """Отправить сообщение пользователю"""
    user_id = int(call.data.split(":")[1])
    
    await state.set_state(States.admin_user_send_message)
    await state.update_data(target_user_id=user_id)
    
    text = f"✉️ <b>ОТПРАВКА СООБЩЕНИЯ</b>\n\n"
    text += f"Пользователь: <code>{user_id}</code>\n\n"
    text += "Отправьте текст сообщения:"
    
    btns = [[types.InlineKeyboardButton(text="◀️ К профилю", callback_data=f"user_profile:{user_id}")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_change_group:"))
@if_admin("call")
async def user_change_group_handler(call: types.CallbackQuery, state: FSMContext):
    """Изменить группу пользователя"""
    user_id = int(call.data.split(":")[1])
    
    await state.set_state(States.admin_user_change_group)
    await state.update_data(target_user_id=user_id, is_secondary=False)
    
    from config import groups
    text = f"✏️ <b>ИЗМЕНЕНИЕ ГРУППЫ</b>\n\n"
    text += f"Пользователь: <code>{user_id}</code>\n\n"
    text += "Отправьте новый номер группы:\n\n"
    text += f"<b>Доступные группы:</b>\n{', '.join(groups[:20])}"
    
    btns = [[types.InlineKeyboardButton(text="◀️ К профилю", callback_data=f"user_profile:{user_id}")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_reset_hours:"))
@if_admin("call")
async def user_reset_hours_handler(call: types.CallbackQuery, state: FSMContext):
    """Сбросить пропуски пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    success = user_manager.reset_user_hours(user_id, call.from_user.id)
    
    if success:
        await call.answer("✅ Пропуски сброшены", show_alert=True)
        # Обновляем профиль
        profile = user_manager.get_user_profile(user_id)
        text = user_manager.format_user_profile(profile)
        
        btns = [
            [types.InlineKeyboardButton(text="📊 История активности", callback_data=f"user_activity:{user_id}")],
            [types.InlineKeyboardButton(text="📈 История пропусков", callback_data=f"user_hours_history:{user_id}")],
            [types.InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data=f"user_send_msg:{user_id}")],
            [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data=f"user_change_group:{user_id}")],
            [types.InlineKeyboardButton(text="🔄 Сбросить пропуски", callback_data=f"user_reset_hours:{user_id}")],
            [types.InlineKeyboardButton(
                text="🚫 Заблокировать" if not profile['is_blocked'] else "✅ Разблокировать",
                callback_data=f"user_toggle_block:{user_id}"
            )],
            [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"user_delete:{user_id}")],
            [ButtonFactory.back("menu:users_management")]
        ]
        
        await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    else:
        await call.answer("❌ Не удалось сбросить пропуски", show_alert=True)


@dp.callback_query(F.data.startswith("user_toggle_block:"))
@if_admin("call")
async def user_toggle_block_handler(call: types.CallbackQuery, state: FSMContext):
    """Заблокировать/разблокировать пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    profile = user_manager.get_user_profile(user_id)
    
    if not profile:
        await call.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    if profile['is_blocked']:
        # Разблокировать
        success = user_manager.unblock_user(user_id, call.from_user.id)
        if success:
            await call.answer("✅ Пользователь разблокирован", show_alert=True)
        else:
            await call.answer("❌ Не удалось разблокировать", show_alert=True)
            return
    else:
        # Заблокировать - запрашиваем причину
        await state.set_state(States.admin_block_reason)
        await state.update_data(target_user_id=user_id)
        
        text = f"🚫 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        text += f"Пользователь: <code>{user_id}</code>\n\n"
        text += "Отправьте причину блокировки:"
        
        btns = [[types.InlineKeyboardButton(text="◀️ К профилю", callback_data=f"user_profile:{user_id}")]]
        
        await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        await call.answer()
        return
    
    # Обновляем профиль
    profile = user_manager.get_user_profile(user_id)
    text = user_manager.format_user_profile(profile)
    
    btns = [
        [types.InlineKeyboardButton(text="📊 История активности", callback_data=f"user_activity:{user_id}")],
        [types.InlineKeyboardButton(text="📈 История пропусков", callback_data=f"user_hours_history:{user_id}")],
        [types.InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data=f"user_send_msg:{user_id}")],
        [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data=f"user_change_group:{user_id}")],
        [types.InlineKeyboardButton(text="🔄 Сбросить пропуски", callback_data=f"user_reset_hours:{user_id}")],
        [types.InlineKeyboardButton(
            text="🚫 Заблокировать" if not profile['is_blocked'] else "✅ Разблокировать",
            callback_data=f"user_toggle_block:{user_id}"
        )],
        [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"user_delete:{user_id}")],
        [ButtonFactory.back("menu:users_management")]
    ]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@dp.callback_query(F.data.startswith("user_delete:"))
@if_admin("call")
async def user_delete_handler(call: types.CallbackQuery, state: FSMContext):
    """Удалить пользователя"""
    user_id = int(call.data.split(":")[1])
    
    text = f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
    text += f"Вы уверены, что хотите удалить пользователя <code>{user_id}</code>?\n\n"
    text += "Это действие необратимо!"
    
    btns = [
        [
            types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"user_delete_confirm:{user_id}"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_profile:{user_id}")
        ]
    ]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_delete_confirm:"))
@if_admin("call")
async def user_delete_confirm_handler(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    success = user_manager.delete_user(user_id, call.from_user.id)
    
    if success:
        text = f"✅ Пользователь <code>{user_id}</code> удален"
        btns = [[ButtonFactory.back("menu:users_management")]]
        
        await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
        await call.answer("✅ Пользователь удален", show_alert=True)
    else:
        await call.answer("❌ Не удалось удалить пользователя", show_alert=True)


@dp.callback_query(F.data.startswith("cleanup_confirm:"))
@if_admin("call")
async def cleanup_confirm_handler(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение очистки неактивных"""
    days = int(call.data.split(":")[1])
    
    await call.answer("⏳ Удаление пользователей...")
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    count = user_manager.cleanup_inactive_users(days, call.from_user.id)
    
    text = f"✅ Очистка завершена\n\n"
    text += f"Удалено пользователей: <b>{count}</b>"
    
    btns = [[ButtonFactory.back("menu:users_management")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_activity:"))
@if_admin("call")
async def user_activity_handler(call: types.CallbackQuery, state: FSMContext):
    """История активности пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    activities = user_manager.get_user_activity_history(user_id, limit=20)
    
    text = f"📊 <b>ИСТОРИЯ АКТИВНОСТИ</b>\n"
    text += f"Пользователь: <code>{user_id}</code>\n\n"
    
    if activities:
        for activity in activities:
            timestamp = activity['timestamp']
            action = activity['action']
            details = activity.get('details', '')
            
            text += f"• <b>{action}</b>\n"
            text += f"  {timestamp}"
            if details:
                text += f"\n  {details}"
            text += "\n\n"
    else:
        text += "Нет записей активности"
    
    btns = [[types.InlineKeyboardButton(text="◀️ К профилю", callback_data=f"user_profile:{user_id}")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("user_hours_history:"))
@if_admin("call")
async def user_hours_history_handler(call: types.CallbackQuery, state: FSMContext):
    """История пропущенных часов пользователя"""
    user_id = int(call.data.split(":")[1])
    
    from utils.admin_user_manager import get_user_manager
    user_manager = get_user_manager()
    
    history = user_manager.get_user_hours_history(user_id, limit=20)
    
    text = f"📈 <b>ИСТОРИЯ ПРОПУСКОВ</b>\n"
    text += f"Пользователь: <code>{user_id}</code>\n\n"
    
    if history:
        for entry in history:
            hours = entry['hours']
            date = entry['date']
            
            sign = "+" if hours > 0 else ""
            text += f"• {sign}{hours}ч - {date}\n"
    else:
        text += "Нет записей об изменении пропусков"
    
    btns = [[types.InlineKeyboardButton(text="◀️ К профилю", callback_data=f"user_profile:{user_id}")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


# Графики аналитики
@dp.callback_query(F.data.startswith("chart:"))
@if_admin("call")
async def chart_handler(call: types.CallbackQuery, state: FSMContext):
    """Отправка графиков"""
    chart_type = call.data.split(":")[1]
    
    from utils.admin_analytics import get_analytics_manager
    from aiogram.types import BufferedInputFile
    
    analytics_manager = get_analytics_manager()
    
    await call.answer("⏳ Генерация графика...")
    
    chart_data = None
    caption = ""
    
    if chart_type == "user_growth":
        chart_data = analytics_manager.generate_user_growth_chart(days=30)
        caption = "📈 График роста пользователей за 30 дней"
    elif chart_type == "activity":
        chart_data = analytics_manager.generate_activity_chart()
        caption = "⚡ Активность пользователей по часам (за 7 дней)"
    elif chart_type == "hours_distribution":
        chart_data = analytics_manager.generate_hours_distribution_chart()
        caption = "📉 Распределение пропущенных часов"
    
    if chart_data:
        photo = BufferedInputFile(chart_data, filename=f"{chart_type}.png")
        await call.message.answer_photo(photo=photo, caption=caption)
    else:
        await call.message.answer("❌ Не удалось создать график")


# Быстрые действия
@dp.callback_query(F.data.startswith("quick:"))
@if_admin("call")
async def quick_actions_handler(call: types.CallbackQuery, state: FSMContext):
    """Обработка быстрых действий"""
    action = call.data.split(":")[1]
    
    from utils.admin_monitoring import get_quick_actions
    quick_actions = get_quick_actions()
    
    if action == "restart_scheduler":
        await call.answer("⏳ Перезапуск планировщика...")
        success = await quick_actions.restart_scheduler(call.from_user.id)
        
        if success:
            await call.message.answer("✅ Планировщик перезапущен")
        else:
            await call.message.answer("❌ Не удалось перезапустить планировщик")
    
    elif action == "clear_cache":
        await call.answer("⏳ Очистка кэша...")
        success = quick_actions.clear_cache(call.from_user.id)
        
        if success:
            await call.message.answer("✅ Кэш очищен")
        else:
            await call.message.answer("❌ Не удалось очистить кэш")
    
    elif action == "update_schedules":
        await call.answer("⏳ Обновление расписаний...")
        stats = await quick_actions.update_all_schedules(call.from_user.id)
        
        text = f"✅ Обновление завершено\n\n"
        text += f"Успешно: {stats['success']}\n"
        text += f"Ошибок: {stats['failed']}"
        
        await call.message.answer(text)
    
    elif action == "test_notification":
        from utils.admin_notifications import notify_admin_custom
        await notify_admin_custom("🔔 Это тестовое уведомление")
        await call.answer("✅ Уведомление отправлено", show_alert=True)
    
    elif action == "check_status":
        from utils.admin_monitoring import get_system_monitor
        system_monitor = get_system_monitor()
        
        health = system_monitor.check_health()
        text = system_monitor.format_health_check(health)
        
        await call.message.answer(text, parse_mode="HTML")
    
    await call.answer()


# Настройки бота
@dp.callback_query(F.data == "menu:toggle_maintenance")
@if_admin("call")
async def toggle_maintenance_handler(call: types.CallbackQuery, state: FSMContext):
    """Переключение режима обслуживания"""
    from utils.maintenance_mode import get_maintenance_mode
    
    maintenance = get_maintenance_mode()
    
    if maintenance.is_enabled():
        success = maintenance.disable(call.from_user.id)
        if success:
            await call.answer("✅ Режим обслуживания выключен", show_alert=True)
        else:
            await call.answer("❌ Не удалось выключить", show_alert=True)
    else:
        success = maintenance.enable(call.from_user.id, reason="")
        if success:
            await call.answer("✅ Режим обслуживания включен", show_alert=True)
        else:
            await call.answer("❌ Не удалось включить", show_alert=True)
    
    # Обновляем меню настроек
    text, btns = await bot_settings(call.from_user.id, state)
    await call.message.edit_text(text, reply_markup=btns, parse_mode="HTML")


@dp.callback_query(F.data.startswith("toggle_admin_notif:"))
@if_admin("call")
async def toggle_admin_notif_handler(call: types.CallbackQuery, state: FSMContext):
    """Переключение настроек уведомлений админу"""
    setting = call.data.split(":")[1]
    
    logger.info(f"Toggle admin notification setting: {setting}")
    
    from utils.admin_notifications import get_admin_notifications
    admin_notif = get_admin_notifications()
    
    setting_map = {
        'main': 'admin_notifications_enabled',
        'critical_errors': 'notify_critical_errors',
        'new_users': 'notify_new_users',
        'error_threshold': 'notify_error_threshold',
        'schedule_problems': 'notify_schedule_problems',
        'disk_space': 'notify_disk_space'
    }
    
    setting_key = setting_map.get(setting)
    if not setting_key:
        logger.warning(f"Unknown setting: {setting}")
        await call.answer("❌ Неизвестная настройка", show_alert=True)
        return
    
    # Получаем текущее значение
    current_value = admin_notif.get_setting(setting_key)
    logger.info(f"Current value for {setting_key}: {current_value}")
    
    # Переключаем
    new_value = '0' if current_value == '1' else '1'
    success = admin_notif.set_setting(setting_key, new_value)
    
    logger.info(f"Set {setting_key} to {new_value}, success: {success}")
    
    status = "включено" if new_value == '1' else "выключено"
    await call.answer(f"✅ {status.capitalize()}", show_alert=False)
    
    # Обновляем меню
    try:
        text, btns = await admin_notifications_settings(call.from_user.id, state)
        await call.message.edit_text(text, reply_markup=btns, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to update menu: {e}", exc_info=True)
        await call.answer("❌ Ошибка обновления меню", show_alert=True)


@dp.callback_query(F.data == "menu:user_export")
@if_admin("call")
async def user_export_handler(call: types.CallbackQuery, state: FSMContext):
    """Экспорт пользователей в Excel"""
    await call.answer("⏳ Создание файла...")
    
    from utils.admin_user_manager import get_user_manager
    from aiogram.types import FSInputFile
    
    user_manager = get_user_manager()
    filepath = user_manager.export_users_to_excel()
    
    if filepath:
        document = FSInputFile(filepath)
        await call.message.answer_document(
            document=document,
            caption="📥 Экспорт пользователей"
        )
    else:
        await call.message.answer("❌ Не удалось создать файл")
    
    await call.answer()


@dp.callback_query(F.data == "menu:user_cleanup")
@if_admin("call")
async def user_cleanup_handler(call: types.CallbackQuery, state: FSMContext):
    """Запрос количества дней для очистки"""
    await state.set_state(States.admin_cleanup_days)
    
    text = "🗑️ <b>ОЧИСТКА НЕАКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
    text += "Отправьте количество дней неактивности\n"
    text += "(например: 30)\n\n"
    text += "Будут удалены пользователи, которые не были\n"
    text += "активны более указанного количества дней."
    
    btns = [[ButtonFactory.back("menu:users_management")]]
    
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


# ============================================================================
# ОБЩИЙ ОБРАБОТЧИК МЕНЮ (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ!)
# ============================================================================

@dp.callback_query(F.data == F.data)
async def inline_handler(call: types.CallbackQuery, state: FSMContext):
    """Общий обработчик для всех callback с префиксом menu:"""
    logger.info(
        "Received callback %s from %s",
        call.data,
        (call.from_user.id, call.from_user.full_name)
    )

    # Работаем только с шаблоном "menu:*"
    if not call.data.startswith("menu:"):
        return

    # Используем безопасную десериализацию
    menu_name, args = CallbackData.decode(call.data)

    menu: Callable | None = globals().get(menu_name)
    if menu is None:
        text = "❌ Меню не найдено"
        btns = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                ButtonFactory.back("menu:start")
            ]]
        )
    else:
        # Пробуем разные варианты сигнатур
        errors_stack = []
        result = None
        try:
            result = await menu(call.message.chat.id, *args, state)
        except Exception as e:
            errors_stack.append(str(e))
            try:
                result = await menu(call.message.chat.id, *args)
            except Exception as e:
                errors_stack.append(str(e))
                try:
                    result = await menu(*args, state)
                except Exception as e:
                    errors_stack.append(str(e))
                    try:
                        result = await menu(call.message.chat.id, state)
                    except Exception as e:
                        errors_stack.append(str(e))
                        errors_stack_str = '\n'.join(f"{idx}. {i}" for idx, i in enumerate(errors_stack, start=1))
                        logger.error(f"Failed to load menu {menu_name}: {errors_stack_str}")
                        text = (
                            "❌ Не удалось загрузить меню\n\n"
                            "💡 Попробуйте:\n"
                            "• Вернуться в главное меню\n"
                            "• Повторить попытку позже\n"
                            "• Обратиться к администратору"
                        )
                        btns = types.InlineKeyboardMarkup(
                            inline_keyboard=[[
                                ButtonFactory.back("menu:start")
                            ]]
                        )
                        result = (text, btns)
        
        # Проверяем тип результата
        if isinstance(result, dict):
            # Специальный формат для фото/документов
            if result.get("type") == "photo":
                await call.message.answer_photo(
                    photo=result["photo"],
                    caption=result.get("caption", "")
                )
                await call.answer()
                return
            elif result.get("type") == "document":
                await call.message.answer_document(
                    document=result["document"],
                    caption=result.get("caption", "")
                )
                await call.answer()
                return
        else:
            text, btns = result
    
    try: 
        await call.message.edit_text(
            text=text,
            reply_markup=btns,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except aiogram.exceptions.TelegramBadRequest:
        await call.answer("ℹ️ Нет изменений...")
    finally:
        await call.answer()
