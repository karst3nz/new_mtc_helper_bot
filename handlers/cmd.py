from config import *
import menus
from log import create_logger
from db import DB
from state import States
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
@check_chat_type("private")
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.settings(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )


@dp.message(Command('rasp'))
@check_chat_type("private")
async def rasp(msg: types.Message, state: FSMContext):
    await state.clear()
    date = msg.text.split("/rasp")[1].replace(" ", '')
    text, btns = await menus.rasp(msg.from_user.id, date=date, _get_new=True)
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


