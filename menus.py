from rasp import Rasp
from log import create_logger
from db import DB
from state import States
from datetime import datetime
logger = create_logger(__name__, level="DEBUG")

async def rasp(user_id: int, date: str = None, _get_new: bool = False):
    group, sec_group = DB().get_user_groups(user_id)
    date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
    rasp = Rasp(date)
    return await rasp.create_rasp_msg(
        group=group,
        sec_group=sec_group,
        _get_new=_get_new
    )


from aiogram import types
from aiogram.fsm.context import FSMContext
async def start(user_id: int, state: FSMContext): 
    if DB().is_exists(user_id) is False:
        text = "Привет! Отправь свою группу:"
        await state.set_state(States.first_reg_group)
        return text, types.InlineKeyboardMarkup(inline_keyboard=[[]])
    else:
        text = "Главное меню"
        btns = [
            [types.InlineKeyboardButton(text="Расписание", callback_data="menu:rasp")],
            [types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def skip_sec_group(user_id: int, state: FSMContext):
    state_data = await state.get_data()
    group = state_data.get("group", "0000")
    await state.clear()
    db = DB()
    db.insert(
        user_id=user_id,
        tg_username=None,
        group_id=group,
        sec_group_id=None
    )
    text, btns = await start(user_id=user_id, state=state)
    return text, btns


async def settings(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    btns = [
        [types.InlineKeyboardButton(text="Изменить основную группу", callback_data="menu:change_main_group")],
        [types.InlineKeyboardButton(text="Изменить доп. группу" if sec_group is not None else "Добавить доп. группу", callback_data="menu:change_sec_group")],
        [types.InlineKeyboardButton(text="< Назад", callback_data="menu:start")]
    ]
    text = "⚙️ Настройки"
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_main_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    text = f"Текущий номер основной группы: {group}\nОтправьте новый номер группы:"
    btns = [
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="menu:settings")]
    ]
    await state.set_state(States.change_main_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)

async def change_sec_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    if sec_group is not None:
        text = f"Текущий номер дополнительной группы: {sec_group}\nОтправьте новый номер группы:"
    else:
        text = "Отправьте номер дополнительной группы:"
    btns = [
        [types.InlineKeyboardButton(text="🗑️ Удалить доп. группу", callback_data="menu:delete_sec_group")],
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="menu:settings")]
    ]
    await state.set_state(States.change_sec_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def delete_sec_group(user_id: int, state: FSMContext):
    db = DB()
    btns = [
        [types.InlineKeyboardButton(text="Вернутся", callback_data="menu:settings")]
    ]
    if db.update(user_id=user_id, column="sec_group_id", new_data=None, table="users") is True:
        text = "Вы успешно удалили дополнительную группу!"
    else:
        text = "При удалении дополнительной группы произошла ошибка!"
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
