import configparser
from datetime import datetime
import logging
import os

def create_logger(__name__=__name__):
    os.makedirs("logs", exist_ok=True)
    read_config = configparser.ConfigParser()
    read_config.read("config.ini") 
    config = read_config['config'] # Словарь с данными из config.ini
    DEBUG = config["DEBUG"]
    # Настройка базового конфигуратора
    logging.basicConfig(
        level=logging.INFO if DEBUG == "False" else logging.DEBUG,                   # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат вывода сообщений
        handlers=[
            logging.StreamHandler(),         # Вывод в консоль
            logging.FileHandler(f"logs/{datetime.now().strftime('%d-%m-%Y')}.log")   # Запись в файл с датой
        ]
    )

    return logging.getLogger(__name__)
