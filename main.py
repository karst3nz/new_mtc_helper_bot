import sys
from threading import Thread
from config import *
from db import DB
from handlers import msg, inline, cmd, state
from log import create_logger


def start_bot():
    asyncio.create_task(dp.start_polling(bot, close_bot_session=False, handle_signals=False))


def create_dirs():
    dirs = ["logs", "data", "data/txt", "data/htm", "db", "data/teach_txt"]
    import os
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)


async def __init__():
    modules = [
        {"name": "создание нужных директорий", "func": create_dirs},
        {"name": "логирование", "func": create_logger, "args": __name__},
        {"name": "БД", "func": DB},
        {"name": "бота", "func": start_bot}
    ]
    for module in modules:
        print(f"Инициализирую {module['name']}... ", end='', flush=False)
        try:
            if "args" in module:
                module["func"](module["args"])
            else:
                module["func"]()
            print("OK")
        except Exception as e:
            print(f"ERROR ({e})")
    else:
        while True:
            await asyncio.sleep(1)



if __name__ == '__main__':
    asyncio.run(__init__())
    # asyncio.run(start_bot(), debug=False)
