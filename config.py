import configparser
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from utils.log import create_logger
import aiogram
from aiogram.filters import CommandStart, Command
from typing import List
from aiogram import F, Router
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

read_config = configparser.ConfigParser()
dp = Dispatcher(storage=MemoryStorage())
logger = create_logger(__name__)

db_DIR = "database/"

read_config.read("config.ini") 

config = read_config['config'] # Словарь с данными из config.ini
BOT_TOKEN = config["bot_token"] if config["bot_token"] is not None else logger.error("Empty parameter for bot_token")
DEBUG = config["DEBUG"] if config["DEBUG"] is not None else logger.error("Empty parameter for DEBUG, using False"); DEBUG=False
ADMIN_ID = config["admin_id"] if config["admin_id"] is not None else logger.error("Empty parameter for admin_id")
SEND_RASP = config["send_rasp"] if config["send_rasp"] is not None else logger.error("Empty parameter for send_rasp")
GOOGLE_DRIVE_KEY = config.get("google_drive_key", None)
GOOGLE_DRIVE_SA_JSON = config.get("google_drive_sa_json", None)
BACKUP_CHAT_ID = config.get("backup_chat_id", ADMIN_ID) if config.get("backup_chat_id", None) is not None else logger.error("Пустое значение для backup_chat_id! Бэкапы отправляю в лс админу...")


groups = [
    "3191", "3395", "3195", "3196", "3391", "3393", "3491", "5111",
    "3495", "3595", "3596", "2191", "2195", "2196", "3392", "4391",
    "4392", "4393", "4394", "4191", "4192", "4193", "4491", "4595",
    "4596", "4311", "4312", "4111", "5391", "5392", "5393", "5394",
    "5191", "5192", "5193", "5491", "5595", "5596", "5311", "5312",
]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
