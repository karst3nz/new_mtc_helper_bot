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


@dp.callback_query(F.data == F.data)
async def inline_handler(call: types.CallbackQuery, state: FSMContext):
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