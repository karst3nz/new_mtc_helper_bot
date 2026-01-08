from datetime import datetime
from config import *
from utils import menus
from utils.log import create_logger
from utils.db import DB
from utils.rasp import Rasp
from utils.state import States
from utils.decorators import check_chat_type, if_admin
logger = create_logger(__name__)


@dp.message(Command("start"))
@check_chat_type("private")
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.start(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )


@dp.message(Command("settings"))
async def settings(msg: types.Message, state: FSMContext):
    await state.clear()
    if msg.chat.type == "private":
        text, btns = await menus.settings(msg.from_user.id, state)
    elif msg.chat.type in ("group", "supergroup"):
        text, btns = await menus.group_settings(msg.chat.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )



@dp.message(Command('rasp'))
@check_chat_type("private")
async def rasp(msg: types.Message, state: FSMContext):
    await state.clear()
    date = msg.text.split("/rasp")[1].replace(" ", '')
    text, btns = await menus.rasp(msg.from_user.id, date=date, _get_new=False)
    await msg.answer(
        text=text,
        reply_markup=btns
    )


@dp.message(Command("hours"))
@check_chat_type("private")
async def hours(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.add_missing_hours(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )



@dp.message(Command("admin"))
@if_admin("msg")
async def admin(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.admin(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )



@dp.message(Command("lesson_schedule"))
@check_chat_type("private")
async def lesson_schedule(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.lesson_schedule(msg.from_user.id if msg.chat.type == "private" else msg.chat.id)
    await msg.answer(
        text=text,
        reply_markup=btns
    )    



# @dp.message(Command("test"))
# async def test(msg: types.Message, state: FSMContext):
#     await state.clear()
#     db = DB()
#     user_id = msg.from_user.id
#     group, sec_group = db.get_user_groups(user_id)
#     rasp = Rasp("08_12_2025"); rasp.show_lesson_time = True; rasp.user_id = user_id
#     text, btns = await rasp.create_rasp_msg(
#         group=group,
#         sec_group=sec_group,
#         _get_new=True,
#         user_id=user_id
#     )
#     user = db.get_user_dataclass(user_id)
#     if "rasp" in str(user.show_missed_hours_mode): text += f"\n⏰ У тебя сейчас <b>{user.missed_hours}</b> пропущенных часов.\n\n"
#     await msg.answer(
#         text=text,
#         reply_markup=btns
#     )
