from config import *

from utils.db import DB
from utils.log import create_logger
from utils.menus import start
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
    await state.clear()
    text = db.return_user_data(str(msg.text))
    btns = [
        [types.InlineKeyboardButton(text='< Назад', callback_data="menu:database")]
    ]
    await msg.answer(text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(States.db_group_info)
@if_admin("msg")
async def db_group_info(msg: types.Message, state: FSMContext):
    db = DB()
    await state.clear()
    text = await db.return_group_data(str(msg.text))
    btns = [
        [types.InlineKeyboardButton(text='< Назад', callback_data="menu:database")]
    ]
    await msg.answer(text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))



@dp.message(States.ad_msg)
@if_admin("msg")
async def ad_msg(msg: types.Message, state: FSMContext):
    await state.set_state(States.ad_confirm)
    await state.update_data(msg2forward=msg)
    msg2delete = []
    msg2delete.append(msg.message_id)
    msg2delete.append((await bot.send_message(chat_id=msg.from_user.id, text=msg.html_text, parse_mode="HTML")).message_id)
    btns = [
        [types.InlineKeyboardButton(text="Да", callback_data="ad_confirm"), types.InlineKeyboardButton(text="Нет", callback_data="ad_deny")]
    ]
    msg2delete.append((await msg.answer(text="Отправлять?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))).message_id)
    await state.update_data(msg2delete=msg2delete)



@dp.message(States.add_missing_hours)
async def add_missing_hours(msg: types.Message, state: FSMContext):
    await state.clear()
    db = DB()
    try:
        hours_to_add = int(msg.text)
    except ValueError:
        await msg.answer("❌ Пожалуйста, введите число.")
        return
    db.cursor.execute("UPDATE users SET missed_hours = missed_hours + ? WHERE user_id = ?", (hours_to_add, msg.from_user.id))
    db.conn.commit()
    user = db.get_user_dataclass(msg.from_user.id)
    btns = [
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    text = f"✅ Готово!\n\n⏰ Теперь у тебя пропущено {user.missed_hours}ч."
    await msg.answer(text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))



@dp.message(States.GROUP_reg_group)
@check_group()
async def GROUP_reg_group(msg: types.Message, state: FSMContext):
    state_data = await state.get_data()
    id = state_data["id"]
    user_id = state_data["user_id"]
    db = DB()
    db.insert_group(id, user_id, msg.text)
    btns = [
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    await msg.reply(f"✅ Группа <b>{msg.text}</b> успешно установлена!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    await state.clear()


@dp.message(States.GROUP_change_group)
@check_group()
async def GROUP_change_group(msg: types.Message, state: FSMContext):
    state_data = await state.get_data()
    id = state_data["id"]
    db = DB()
    db.cursor.execute('UPDATE groups SET "group" = ? WHERE id = ?', (msg.text, id))
    db.conn.commit()
    btns = [
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    await msg.reply(f"✅ Группа <b>{msg.text}</b> успешно установлена!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
    await state.clear()