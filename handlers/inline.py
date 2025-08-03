import aiogram.exceptions
from config import *
from log import create_logger
import ast
from typing import Callable
from menus import *
logger = create_logger(__name__)


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

    await state.clear()

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
        try:
            text, btns = await menu(call.from_user.id, *args, state)
        except Exception as e:
            logger.error(e)
            try:
                text, btns = await menu(call.from_user.id, *args)
            except Exception as e:
                logger.error(e)
                try:
                    text, btns = await menu(*args, state)
                except Exception as e:
                    logger.error(e)
                    try:
                        text, btns = await menu(call.from_user.id, state)
                    except Exception as e:
                        logger.error(e)
                        text = "❌ Не удалось загрузить меню"
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
        await call.answer("Нет изменений...")
    finally:
        await call.answer()