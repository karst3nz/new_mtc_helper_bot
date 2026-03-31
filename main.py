import signal
import asyncio
from config import bot, dp, types
from utils.db import DB
from handlers import msg, inline, cmd, event, quick_commands, inline_query
from utils.log import create_logger
from utils import check_groups, delete_users
from utils.rasp import CheckRasp
from utils.notifications import get_notification_manager



def start_bot():
    # Регистрируем роутеры из новых модулей
    dp.include_router(quick_commands.router)
    dp.include_router(inline_query.router)
    asyncio.create_task(dp.start_polling(bot, close_bot_session=False, handle_signals=False))

def start_notifications():
    """Запуск системы уведомлений"""
    notification_manager = get_notification_manager()
    notification_manager.start()


def cmds():
    asyncio.create_task(bot.set_my_commands([
        types.BotCommand(command="start", description="🎓 Главное меню"),
        types.BotCommand(command="settings", description="⚙️ Настройки"),
        types.BotCommand(command="hours", description="⏰ Пропущенные часы"),
        types.BotCommand(command="lesson_schedule", description="🔔 Расписание звонков")
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

    async def update_users():
        from utils.users_data_update import update
        await update()

    # Бэкап БД в 3:00 ночи каждый день
    crontab('0 3 * * *')(backup_job)

    # Обновление данных в 4:00 ночи каждый день
    crontab('0 4 * * *')(update_users)

    # Тестовый бэкап через 10 секунд после запуска
    # crontab('*/10 * * * * *', start=True, loop=None)(update_users)


async def init_custom_api_if_needed():
    """Инициализация кастомного API сервера и бота, если нужно"""
    import config
    from config import CUSTOM_API_URL, BOT_TOKEN, session, wait_for_api_server, start_custom_api_server
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    
    if CUSTOM_API_URL:
        # Запускаем API сервер
        if not start_custom_api_server():
            # Если event loop еще не был создан, создаем задачу сейчас
            from custom_bot_api.run import run
            asyncio.create_task(run())
        
        # Ждем готовности API сервера
        logger = create_logger(__name__)
        logger.info("Ожидание готовности кастомного Bot API сервера...")
        if await wait_for_api_server(CUSTOM_API_URL):
            # Создаем bot с кастомной сессией и обновляем в config модуле
            config.bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            ))
            # Также обновляем глобальную переменную bot для текущего модуля
            global bot
            bot = config.bot
            logger.info("Бот инициализирован с кастомным API сервером")
            return True
        else:
            logger.error("Кастомный Bot API сервер не запустился за 30 секунд, завершение работы.")
            return False
    return True


async def shutdown_handler():
    """Обработчик завершения работы"""
    global shutdown_flag
    shutdown_flag = True
    
    logger = create_logger(__name__)
    logger.info("Получен сигнал завершения, начинаю корректное завершение...")
    
    # Завершаем сессию бота
    try:
        if bot and bot.session:
            logger.info("Закрытие сессии бота...")
            await bot.session.close()
            logger.info("Сессия бота закрыта")
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии бота: {e}")
    
    # Завершаем API сервер, если он запущен
    try:
        from custom_bot_api.run import shutdown_api_server
        await shutdown_api_server()
    except Exception as e:
        logger.error(f"Ошибка при завершении API сервера: {e}")
    
    logger.info("Завершение работы завершено")


def setup_signal_handlers():
    """Настройка обработчиков сигналов для asyncio"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Если event loop еще не запущен, вернемся к этому позже
        return
    
    def signal_handler(signum):
        """Обработчик сигналов SIGINT и SIGTERM"""
        logger = create_logger(__name__)
        logger.info(f"Получен сигнал {signum}, инициирую завершение...")
        # Создаем задачу для корректного завершения
        asyncio.create_task(shutdown_handler())
    
    # Регистрируем обработчики для SIGINT (Ctrl+C) и SIGTERM
    # Используем add_signal_handler для корректной работы с asyncio
    try:
        loop.add_signal_handler(signal.SIGINT, lambda: signal_handler(signal.SIGINT))
        loop.add_signal_handler(signal.SIGTERM, lambda: signal_handler(signal.SIGTERM))
    except NotImplementedError:
        # На Windows add_signal_handler может не работать, используем обычный signal
        def signal_handler_fallback(signum, frame):
            signal_handler(signum)
        signal.signal(signal.SIGINT, signal_handler_fallback)
        signal.signal(signal.SIGTERM, signal_handler_fallback)


# Флаг для корректного завершения
shutdown_flag = False

async def __init__():
    global shutdown_flag
    
    # Инициализация кастомного API сервера, если нужно
    if not await init_custom_api_if_needed():
        quit(1)
    
    # Настраиваем обработчики сигналов после инициализации event loop
    setup_signal_handlers()
    
    modules = [
        {"name": "создание нужных директорий", "func": create_dirs},
        {"name": "логирование", "func": create_logger, "args": __name__},
        {"name": "БД", "func": DB},
        {"name": "бэкап БД", "func": db_backup},
        # {"name": "проверку групп в конфиге", "func": check_groups.run},
        # {"name": "удаление пользователей с неиспользуемыми ботом группами", "func": delete_users.run},
        {"name": "бота", "func": start_bot},
        {"name": "установку команд", "func": cmds},
        {"name": "систему уведомлений", "func": start_notifications},
        # {"name": "цикличную проверку расписания", "func": rasp_loop},
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
        try:
            while not shutdown_flag: # Основной цикл asyncio, все остальное запущено как task
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            # Дополнительная обработка Ctrl+C на случай, если сигнал не сработал
            logger = create_logger(__name__)
            logger.info("Получен KeyboardInterrupt, завершаю работу...")
            shutdown_flag = True
            await shutdown_handler()



if __name__ == '__main__':
    asyncio.run(__init__())
