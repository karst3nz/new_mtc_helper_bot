import sys
from threading import Thread
from config import *
from utils.db import DB
from handlers import msg, inline, cmd, event
from utils.log import create_logger


def start_bot():
    asyncio.create_task(dp.start_polling(bot, close_bot_session=False, handle_signals=False))


def cmds():
    asyncio.create_task(bot.set_my_commands([
        types.BotCommand(command="/start", description="🎓 Главное меню"),
        types.BotCommand(command="/settings", description="⚙️ Настройки"),
        types.BotCommand(command="/hours", description="⏰ Пропущенные часы"),
    ]))

def create_dirs():
    dirs = ["data", "data/txt", "database", 'data/old_txt']
    import os
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)


async def __init__():
    modules = [
        {"name": "создание нужных директорий", "func": create_dirs},
        {"name": "логирование", "func": create_logger, "args": __name__},
        {"name": "БД", "func": DB},
        {"name": "бота", "func": start_bot},
        {"name": "установку команд", "func": cmds}
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
            quit(1)
    else:
        while True:
            await asyncio.sleep(1)



if __name__ == '__main__':
    asyncio.run(__init__())
    # asyncio.run(start_bot(), debug=False)
