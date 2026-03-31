import configparser
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from utils.log import create_logger
import aiogram
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
import asyncio
from aiogram import types
from utils.state import States
from aiogram.filters.chat_member_updated import \
    ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER, ADMINISTRATOR
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если существует)
load_dotenv()

read_config = configparser.ConfigParser()
dp = Dispatcher(storage=MemoryStorage())
logger = create_logger(__name__)

# Регистрация роутеров будет выполнена в main.py после импорта handlers

db_DIR = "database/"

# Пытаемся прочитать config.ini для обратной совместимости
read_config.read("config.ini") 

def get_config_value(key: str, default=None, required: bool = False):
    """
    Получает значение конфигурации из переменных окружения или config.ini.
    Приоритет: переменные окружения > config.ini > default
    """
    # Сначала проверяем переменные окружения
    env_value = os.getenv(key.upper())
    if env_value is not None:
        return env_value
    
    # Затем проверяем config.ini
    if read_config.has_section('config'):
        ini_value = read_config['config'].get(key)
        if ini_value is not None:
            return ini_value
    
    # Используем значение по умолчанию
    if default is not None:
        return default
    
    # Если параметр обязательный и не найден, выбрасываем ошибку
    if required:
        logger.error(f"Empty parameter for {key}")
        raise ValueError(f"{key} is required in .env or config.ini")
    
    return None

BOT_TOKEN = get_config_value("bot_token", required=True)

DEBUG = get_config_value("DEBUG", "False")
DEBUG = DEBUG.lower() in ("1", "true", "yes")

ADMIN_ID = get_config_value("admin_id", required=True)

SEND_RASP = get_config_value("send_rasp", required=True)

BACKUP_CHAT_ID = get_config_value("backup_chat_id", ADMIN_ID)
if BACKUP_CHAT_ID is None:
    logger.error("Пустое значение для backup_chat_id! Бэкапы отправляю в лс админу...")
    BACKUP_CHAT_ID = ADMIN_ID

API_ID = get_config_value("api_id")
API_HASH = get_config_value("api_hash")

# URL кастомного Bot API сервера (если не указан, используется официальный API)
CUSTOM_API_URL = get_config_value("custom_api_url")

groups = [
    "3191", "3395", "3195", "3196", "3391", "3393", "3491", "5111",
    "3495", "3595", "3596", "2191", "2195", "2196", "3392", "4391",
    "4392", "4393", "4394", "4191", "4192", "4193", "4491", "4595",
    "4596", "4311", "4312", "4111", "5391", "5392", "5393", "5394",
    "5191", "5192", "5193", "5491", "5595", "5596", "5311", "5312",
]


async def wait_for_api_server(url: str, timeout: int = 30):
    """Ожидание готовности API сервера через HTTP запрос"""
    import aiohttp
    import time
    
    start_time = time.time()
    check_url = f"{url}/bot{BOT_TOKEN}/getMe"
    
    logger.info(f"Проверка готовности API сервера на {check_url}")
    
    while time.time() - start_time < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(check_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            logger.info("Кастомный Bot API сервер готов!")
                            return True
        except Exception as e:
            # Сервер еще не готов, продолжаем ждать
            pass
        
        await asyncio.sleep(1)
    
    logger.error(f"API сервер не ответил за {timeout} секунд")
    return False


def start_custom_api_server():
    """Запуск кастомного API сервера в фоновой задаче"""
    from custom_bot_api.run import run
    # Запускаем в фоновой задаче, чтобы не блокировать основной поток
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(run())
        logger.info("Запущена фоновая задача для telegram-bot-api")
    except RuntimeError:
        # Если event loop еще не создан, создадим задачу позже
        logger.warning("Event loop еще не создан, API сервер будет запущен позже")
        return False
    return True


# Настройка кастомного API сервера (если указан URL)
if CUSTOM_API_URL:
    logger.info(f"Использование кастомного Bot API сервера: {CUSTOM_API_URL}")
    api_server = TelegramAPIServer.from_base(CUSTOM_API_URL)
    session = AiohttpSession(api=api_server)
    # Бот будет создан в main.py после ожидания готовности API сервера
    bot = None
else:
    logger.info("Использование официального Telegram Bot API")
    session = None
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ))

