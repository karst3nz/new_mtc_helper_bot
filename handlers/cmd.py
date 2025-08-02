from re import T
from config import *
import menus
from log import create_logger
from db import DB
from state import States
logger = create_logger(__name__)


@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.start(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )


@dp.message(Command("settings"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    text, btns = await menus.settings(msg.from_user.id, state)
    await msg.answer(
        text=text,
        reply_markup=btns
    )


@dp.message(Command('rasp'))
async def rasp(msg: types.Message):
    date = msg.text.split("/rasp")[1].replace(" ", '')
    text, btns = await menus.rasp(msg.from_user.id, date=date, _get_new=True)
    await msg.answer(
        text=text,
        reply_markup=btns
    )
# from test import compare_texts
# @dp.message(Command("test"))
# async def test(msg: types.Message):
#     замена_text1 = """
# 3 | test | 000 | test_teach
# 4 | test | 000 | test_teach
# 5 | test | 010 | test_teach
# """

#     замена_text2 = """
# 3 | test | 000 | test_teach
# 4 | test123 | 000 | test_teach
# 5 | test | 010 | test_teach
# """

#     add_text1 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# """

#     add_text2 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# 3 | test | 020 | test_teach
# """
#     remove_text1 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# 3 | test | 010 | test_teach
# """

#     remove_text2 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# """
    
#     await msg.answer(text=f'Добавление:\n{compare_texts(add_text1, add_text2)}')
#     await msg.answer(text=f'Удаление:\n{compare_texts(remove_text1, remove_text2)}')
#     await msg.answer(text=f'Замена:\n{compare_texts(замена_text1, замена_text2)}')
