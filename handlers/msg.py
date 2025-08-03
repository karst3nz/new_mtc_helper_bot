from config import *

from db import DB
from log import create_logger
from menus import start
from utils.decorators import check_group, if_admin
logger = create_logger(__name__)


@dp.message(States.first_reg_group)
@check_group()
async def reg_group(msg: types.Message, state: FSMContext):
    btns = [
        [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="menu:skip_sec_group")]
    ]
    await msg.answer("🎯 Отлично! Группа <b>{}</b> добавлена.\n\n💡 Хотите добавить дополнительную группу?\n\n📋 В расписании будет отображаться расписание обеих групп.\n\n⏭️ Этот шаг можно пропустить.".format(msg.text),
                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns)
    )
    await state.set_state(States.sec_reg_group)
    await state.update_data(group=msg.text)



@dp.message(States.sec_reg_group)
@check_group()
async def sec_reg_group(msg: types.Message, state: FSMContext):
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
@check_group()
async def change_main_group(msg: types.Message, state: FSMContext):
    db = DB()
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="◀️ Вернуться", callback_data="menu:settings")]
    ]
    if db.update(user_id=msg.from_user.id, column="group_id", new_data=msg.text, table='users') is True:
        await msg.answer("✅ Основная группа успешно изменена!\n\n📋 Новый номер: <b>{}</b>".format(msg.text), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await msg.answer("❌ Не удалось изменить номер группы.\n\n🔧 Попробуйте позже или обратитесь к администратору.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(States.change_sec_group)
@check_group()
async def change_sec_group(msg: types.Message, state: FSMContext):
    db = DB()
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="◀️ Вернуться", callback_data="menu:settings")]
    ]
    if db.update(user_id=msg.from_user.id, column="sec_group_id", new_data=msg.text, table='users') is True:
        await msg.answer("✅ Дополнительная группа успешно изменена!\n\n📋 Новый номер: <b>{}</b>".format(msg.text), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await msg.answer("❌ Не удалось изменить номер группы.\n\n🔧 Попробуйте позже или обратитесь к администратору.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(States.db_user_info)
@if_admin('msg')
async def db_user_info(msg: types.Message, state: FSMContext):
    db = DB()
    text = db.return_user_data(str(msg.text))
    btns = [
        [types.InlineKeyboardButton(text='< Назад', callback_data="menu:database")]
    ]
    await msg.answer(text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))