import sys
from threading import Thread
from config import *
from utils.db import DB
from handlers import msg, inline, cmd, event
from utils.log import create_logger
from utils import check_groups, delete_users
from utils.rasp import CheckRasp



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


def rasp_loop():
    async def _run():
        while True:
            from datetime import datetime, timedelta
            tomorrow = datetime.now().date() + timedelta(days=1)
            if tomorrow.weekday() == 6:
                tomorrow = tomorrow + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%d_%m_%Y")
            cr = CheckRasp(date=tomorrow_str)
            await cr.check_rasp_loop()
    asyncio.create_task(_run())
            



def db_backup():
    from aiogram import Bot
    from aiocron import crontab

    async def backup_job():
        from utils.tg_db_backup import send_db_to_admin
        await send_db_to_admin()

    # Бэкап в 3:00 ночи каждый день
    crontab('0 3 * * *')(backup_job)
    # Тестовый бэкап через 10 секунд после запуска
    # crontab('*/10 * * * * *', start=True, loop=None)(backup_job)


async def __init__():
    modules = [
        {"name": "создание нужных директорий", "func": create_dirs},
        {"name": "логирование", "func": create_logger, "args": __name__},
        {"name": "БД", "func": DB},
        {"name": "бэкап БД", "func": db_backup},
        # {"name": "проверку групп в конфиге", "func": check_groups.run},
        # {"name": "удаление пользователей с неиспользуемыми ботом группами", "func": delete_users.run},
        {"name": "бота", "func": start_bot},
        {"name": "установку команд", "func": cmds},
        {"name": "цикличную проверку расписания", "func": rasp_loop}
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
        while True: # Основной цикл asyncio, все остальное запущено как task
            await asyncio.sleep(1)



if __name__ == '__main__':
    asyncio.run(__init__())
