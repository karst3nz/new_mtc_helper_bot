from re import T
import aiogram.exceptions
from config import *
from utils.log import create_logger
from typing import Callable
from utils.menus import *
import ast
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
                await msg2forward.forward(chat_id=user_id)
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
        await call.message.edit_text(text='✅ Права выданы верно!', reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='❌ Закрыть', callback_data='delete_msg')]]))
    except:
        await call.message.reply("❌ Проверка не удалась, проверьте права бота!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='❌ Закрыть', callback_data='delete_msg')]]))

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

    menu_data = call.data[len("menu:"):]
    if "?" in menu_data:
        menu_name, raw_args = menu_data.split("?", 1)
        # В rare-case, когда строка заканчивается на "?", аргументов нет.
        raw_args = raw_args.strip()
        if raw_args:
            try:
                args = ast.literal_eval(raw_args)
            except (ValueError, SyntaxError):
                logger.warning("Не удалось спарсить аргументы: %s", raw_args)
                args = ()
        else:
            args = ()
    else:
        menu_name, args = menu_data, ()

    # Если parsed object не кортеж — превращаем в кортеж
    if not isinstance(args, tuple):
        args = (args,)

    menu: Callable | None = globals().get(menu_name)
    if menu is None:
        text = "❌ Меню не найдено"
        btns = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:start")
            ]]
        )
    else:
        # Пробуем разные варианты сигнатур
        errors_stack = []
        try:
            text, btns = await menu(call.message.chat.id, *args, state)
        except Exception as e:
            errors_stack.append(str(e))
            # logger.error(e)
            try:
                text, btns = await menu(call.message.chat.id, *args)
            except Exception as e:
                errors_stack.append(str(e))
                # logger.error(e)
                try:
                    text, btns = await menu(*args, state)
                except Exception as e:
                    errors_stack.append(str(e))
                    # logger.error(e)
                    try:
                        text, btns = await menu(call.message.chat.id, state)
                    except Exception as e:
                        errors_stack.append(str(e))
                        errors_stack_str = '\n'.join(f"{idx}. {i}" for idx, i in enumerate(errors_stack, start=1))
                        logger.error(e)
                        text = f"❌ Не удалось загрузить меню. Стэк ошибок:\n<code>{errors_stack_str}</code>"
                        btns = types.InlineKeyboardMarkup(
                            inline_keyboard=[[
                                types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:start")
                            ]]
                        )
    try: await call.message.edit_text(
        text=text,
        reply_markup=btns,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    except aiogram.exceptions.TelegramBadRequest:
        await call.answer("ℹ️ Нет изменений...")
    finally:
        await call.answer()