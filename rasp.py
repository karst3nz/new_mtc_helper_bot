from datetime import datetime, timedelta
import os
import tempfile
import time
import aiohttp
from aspose.cells import Workbook
from log import create_logger
from config import *


class Rasp:
    def __init__(self, date: str) -> None:
        print("__init__ --> ", end="", flush=True)
        self.date = date
        self.dateWyear = date.split('_')[:2][0] + "_" +date.split('_')[:2][1]
        self.filename = f"PODNAM%20{self.dateWyear}.htm"
        self.txt_filename = f"{date}.txt"
        self.base_txt_dir = "data/txt"
        self.txt_dir = os.path.join(self.base_txt_dir, self.txt_filename)
        self.url = f"https://bseumtc.by/schedule/public/rasp/{self.filename}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "ru-RU,ru;q=0.5",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": "\"Chromium\";v=\"136\", \"Brave\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1"
        }

        self.logger = create_logger(__name__)
        self.logger.debug(f"Инициализация Rasp с датой: {self.date}")

    async def run_session(self):
        print("run_session --> ", end="", flush=False)
         
        self.logger.debug("Запуск сессии")
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):
        print("close_session --> ", end="", flush=True)
         
        self.logger.debug("Закрытие сессии")
        await self.session.close()

    async def _make_request(self):
        print("_make_request --> ", end="", flush=True)
         
        self.logger.debug(f"Отправка запроса на {self.url}")
        await self.run_session()
        async with self.session.get(self.url) as response:
            r = await response.read()
            self.logger.debug(f"Запрос выполнен успешно, статус: {response.status}")
            await self.close_session()
            return r

    def convert_htm2txt(self):
        print("convert_htm2txt --> ", end="", flush=True)
         
        self.logger.debug("Конвертация HTML в TXT")
        workbook = Workbook(self.temp_file_dir)
        if os.path.exists(self.txt_dir):
            self.logger.debug(f"Файл {self.txt_dir} уже существует, удаление")
            os.remove(self.txt_dir)
        workbook.save(self.txt_dir)
        self.logger.debug(f"Файл сохранен как {self.txt_dir}")

    async def get(self):
        print("get --> ", end="", flush=True)
         
        self.logger.debug("Получение данных")
        self.rasp_response = await self._make_request()
        self.temp_file_dir = os.path.join(tempfile.gettempdir(), f'{self.date}.htm')
        with open(self.temp_file_dir, 'wb') as temp_file:
            self.logger.debug(f"Запись данных во временный файл {self.temp_file_dir}")
            temp_file.write(self.rasp_response)
        self.logger.debug("Данные успешно записаны во временный файл")
        self.convert_htm2txt()

    def rasp_parse(self, group):
        print("rasp_parse --> ", end="", flush=True)
         
        rasp_list = []
        rasp_list_done = []
        classes = [f"¦{group}¦"]
        
        if not os.path.isfile(self.txt_dir):
            self.logger.debug("Расписание не найдено")
            return ['Расписания нету!']

        with open(self.txt_dir, "r", encoding="windows-1251") as file:
            content = file.read()

        lines = content.splitlines()
        inside_classes = False  # Флаг, указывающий, что мы находимся внутри уроков из classes

        for line in lines:
            if any(separator in line for separator in ["+----+--+--------------+---+---------------+", "L----+--+--------------+---+----------------", "Evaluation Only"]):
                inside_classes = False
                continue  # Пропустить строку-разделитель

            if inside_classes:
                if line.strip():  # Проверка, что строка не пустая или состоит только из пробелов
                    rasp_list.append(line)
                else:
                    inside_classes = False
                continue  # Перейти к следующей строке

            if any(class_item in line for class_item in classes):
                rasp_list.append(line)
                inside_classes = True

        if rasp_list:
            rasp_info = self.rasp_data_get(rasp_list)
            if isinstance(rasp_info, dict):
                lesson_number_to_lookup = max(item['lesson_id'] for item in rasp_info.values() if item['lesson_id'])
                lesson_id = min(item['lesson_id'] for item in rasp_info.values() if item['lesson_id']) - 1
                
                while lesson_id < lesson_number_to_lookup:
                    lesson_id += 1
                    rasp_info_process = rasp_info.get(lesson_id)
                    if rasp_info_process:
                        rasp_list_done.append(
                            f"{rasp_info_process['lesson_number']} | {rasp_info_process['subject']} "
                            f"| {rasp_info_process['classroom_number']} | {rasp_info_process['teacher']}"
                        )
                        self.logger.debug(f"Добавлено расписание: {rasp_info_process}")

            return rasp_list_done

        self.logger.debug("Расписания нету!")
        return ['Расписания нету!']

    def rasp_data_get(self, schedule_data) -> dict:
        print("rasp_data_get --> ", end="", flush=True)
         
        schedule_info = {}
        lesson_id = 0
        # Проходим по строкам расписания
        for line in schedule_data:
            # Разбиваем строку на части, используя символ "¦" как разделитель
            parts = line.split('¦')
            lesson_id += 1
            # Извлекаем нужные элементы информации
            group_number = parts[1].strip() if parts[1].strip() else None
            lesson_number = parts[2].strip()
            subject = parts[3].strip()
            classroom_number = parts[4].strip()
            teacher = parts[5].strip()
            # Формируем ключ для словаря (номер урока)
            if lesson_number != '':
                lesson_key = int(lesson_number)
            elif lesson_number == '':
                lesson_number = ''
                lesson_key = ''
            else:
                lesson_key = ''
            # Сохраняем информацию в словаре
            schedule_info[lesson_id] = {
                'lesson_id': lesson_id,
                'lesson_number': lesson_number,
                'group_number': group_number,
                'subject': subject,
                'classroom_number': classroom_number,
                'teacher': teacher,
            }
            self.logger.debug(f"Урок {lesson_id}: {schedule_info[lesson_id]}")

        return schedule_info

    async def get_rasp(self, group: int, _get_new: bool = False):
        print("get_rasp --> ", end="", flush=True)
         
        self.logger.debug(f"Получение расписания для группы: {group}")
        if _get_new is True: 
            await self.get()
        _rasp = self.rasp_parse(group)
        return "\n".join(_rasp)

    @staticmethod
    def days_of_week(date: str):
        print("days_of_week --> ", end="", flush=True)
        date_format = "%d_%m_%Y"
        date_object = datetime.strptime(date, date_format).date()
        days_of_week_ru = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        day_of_week = date_object.weekday()
        days_week = days_of_week_ru[day_of_week]
        return days_week

    async def create_rasp_msg(self, group: int, sec_group: int = None, _get_new: bool = False):
        print("create_rasp_msg --> ", end="", flush=True)
        _rasp_text = await self.get_rasp(group, _get_new)
        day_of_week = str(self.days_of_week(self.date))
        sec_head_text = ''
        _sec_rasp_text = ''
        if sec_group is not None:
            sec_head_text = f"<b>________________________________________</b>\n\n<b>{self.date.replace('_', '.')}           {day_of_week}           {sec_group}</b>"
            _sec_rasp_text += await self.get_rasp(sec_group, _get_new)
        
        head_text = f"<b>{self.date.replace('_', '.')}           {day_of_week}           {group}</b>"
        text = f"""
{head_text}

{_rasp_text}

{sec_head_text}

{_sec_rasp_text}
"""
        dateObj = datetime.strptime(self.date, "%d_%m_%Y").date()        
        back_btn = (dateObj - timedelta(days=1)).strftime("%d_%m_%Y")
        reload_btn = dateObj.strftime("%d_%m_%Y")
        next_btn = (dateObj + timedelta(days=1)).strftime("%d_%m_%Y")
        btns = [
            [types.InlineKeyboardButton(text="◀️", callback_data=f"menu:rasp?{(back_btn, False)}"), 
             types.InlineKeyboardButton(text="🔄", callback_data=f"menu:rasp?{(reload_btn, True)}"), 
             types.InlineKeyboardButton(text="▶️", callback_data=f"menu:rasp?{(next_btn, False)}")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def main():
    rasp = Rasp("12_05_2025")
    text, btns = await rasp.create_rasp_msg("3395", _get_new=False)
    await bot.send_message(
        chat_id="1823563959",
        text=text,
        reply_markup=btns
    )


async def test():
    text = f"""
<b>Расписание изменилось!</b>
<b>12.05.2025           ПОНЕДЕЛЬНИК           0000</b>

<s>1 | test_del | 000 | test_teach</s>
<b>1 | test_ins | 000 | test_teach</b>
2 | test | 000 | test_teach

Ты пропустил 0ч.
"""
    await bot.send_message(
        chat_id="1823563959",
        text=text
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(test())