from config import *

from db import DB
from log import create_logger
from menus import start
logger = create_logger(__name__)


@dp.message(States.first_reg_group)
async def reg_group(msg: types.Message, state: FSMContext):
    if str(msg.text) not in groups:
        await msg.answer(f"Я не знаю такую группу :(")
        return
    btns = [
        [types.InlineKeyboardButton(text="Пропустить ➡️", callback_data="menu:skip_sec_group")]
    ]
    await msg.answer("Может хочешь добавить дополнительную группу? \nВ расписании также будет отображаться ее расписание. \nЭтот этап можно пропустить",
                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns)
    )
    await state.set_state(States.sec_reg_group)
    await state.update_data(group=msg.text)



@dp.message(States.sec_reg_group)
async def sec_reg_group(msg: types.Message, state: FSMContext):
    if str(msg.text) not in groups:
        await msg.answer(f"Я не знаю такую группу :(")
        return
    state_data = await state.get_data()
    group = state_data.get("group", "0000")
    await state.clear()
    db = DB()
    db.insert(
        user_id=msg.from_user.id,
        tg_username=msg.from_user.username,
        group_id=group,
        sec_group_id=msg.text
    )
    text, btns = await start(user_id=msg.from_user.id, state=state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )
    

@dp.message(States.change_main_group)
async def change_main_group(msg: types.Message, state: FSMContext):
    if str(msg.text) not in groups:
        await msg.answer(f"Я не знаю такую группу :(")
        return
    db = DB()
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="Вернутся", callback_data="menu:settings")]
    ]
    if db.update(user_id=msg.from_user.id, column="group_id", new_data=msg.text, table='users') is True:
        await msg.answer(f"Вы успешно изменили номер основной группы!\nНовый номер: {msg.text}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await msg.answer(f"Не удалось изменить номер группы :(", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(States.change_sec_group)
async def change_main_group(msg: types.Message, state: FSMContext):
    if str(msg.text) not in groups:
        await msg.answer(f"Я не знаю такую группу :(")
        return
    db = DB()
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="Вернутся", callback_data="menu:settings")]
    ]
    if db.update(user_id=msg.from_user.id, column="sec_group_id", new_data=msg.text, table='users') is True:
        await msg.answer(f"Вы успешно изменили номер дополнительной группы!\nНовый номер: {msg.text}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await msg.answer(f"Не удалось изменить номер группы :(", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
