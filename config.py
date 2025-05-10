import configparser
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from log import create_logger
import aiogram
from aiogram.filters import CommandStart, Command
from typing import List
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
import asyncio
from aiogram import types
from aiogram import F
from state import States
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
DEBUG = config["DEBUG"] if config["DEBUG"] is not None else logger.error("Empty parameter for DEBUG")


# Проверка на правильность токена бота
try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ))
except aiogram.utils.token.TokenValidationError:
    logger.critical("Bot token are empty or invalid")