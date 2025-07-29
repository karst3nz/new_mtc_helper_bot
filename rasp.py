from datetime import datetime, timedelta
import os
import tempfile
import time
import aiohttp
from aspose.cells import Workbook
from db import DB
from log import create_logger
from config import *


class Rasp:
    def __init__(self, date: str = None, is_teacher: bool = False) -> None:
        self.is_teacher = is_teacher
        self.logger = create_logger("Rasp", level="DEBUG")
        self.date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
        self.logger.debug(f"Инициализация Rasp с датой: {self.date}")
        self.dateWyear = self.date.split('_')[:2][0] + "_" + self.date.split('_')[:2][1]
        self.rasp_exists = False
        if not self.is_teacher:
            self.filename = f"PODNAM%20{self.dateWyear}.htm"
            self.txt_filename = f"{self.date}.txt"
            self.base_txt_dir = "data/txt"
            self.txt_dir = os.path.join(self.base_txt_dir, self.txt_filename)
        else:
            self.filename = f"SETKA%20{self.dateWyear}.htm"
            self.txt_filename = f"{self.date}.txt"
            self.base_txt_dir = "data/teach_txt"
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



    async def run_session(self): 
        self.logger.debug("Запуск сессии")
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):  
        self.logger.debug("Закрытие сессии")
        await self.session.close()

    async def _make_request(self):
        await self.run_session()
        self.logger.debug(f"Отправка запроса на {self.url}")
        async with self.session.get(self.url) as response:
            if response.status >= 400:
                self.logger.debug(f"Запрос выполнен неуспешно, статус: {response.status}")
                self.rasp_exists = False
                await self.close_session()
                return None 
            else:
                r = await response.read()
                self.logger.debug(f"Запрос выполнен успешно, статус: {response.status}")
                self.rasp_exists = True
                await self.close_session()
                return r

    def convert_htm2txt(self):
        self.logger.debug("Конвертация HTML в TXT")
        workbook = Workbook(self.temp_file_dir)
        if os.path.exists(self.txt_dir):
            self.logger.debug(f"Файл {self.txt_dir} уже существует, удаление")
            os.remove(self.txt_dir)
        workbook.save(self.txt_dir)
        self.logger.debug(f"Файл сохранен как {self.txt_dir}")

    async def get(self):
        self.logger.debug("Получение данных")
        self.rasp_response = await self._make_request()
        if self.rasp_response is None:
            return
        self.temp_file_dir = os.path.join(tempfile.gettempdir(), f'{self.date}.htm')
        with open(self.temp_file_dir, 'wb') as temp_file:
            self.logger.debug(f"Запись данных во временный файл {self.temp_file_dir}")
            temp_file.write(self.rasp_response)
        self.logger.debug("Данные успешно записаны во временный файл")
        self.convert_htm2txt()

    def group_rasp_parse(self, group):
        rasp_list = []
        rasp_list_done = []
        classes = [f"¦{group}¦"]
        
        if not os.path.isfile(self.txt_dir):
            self.logger.debug("Расписание не найдено")
            self.rasp_exists = False
            return ['Расписания нету!']
        else:
            self.rasp_exists = True

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

    def rasp_parse(self, teach: str):
        rasp_list = []
        rasp_list_done = []
        classes = [f"¦{teach}¦"]
        
        if not os.path.isfile(self.txt_dir):
            self.logger.debug("Расписание не найдено")
            return ['Расписания нету!']

        with open(self.txt_dir, "r", encoding="windows-1251") as file:
            content = file.read()

        lines = content.splitlines()
        inside_classes = False  # Флаг, указывающий, что мы находимся внутри уроков из classes

        for line in lines:
            line = line.replace(" ", '').replace("\xa0", "")
            if any(separator in line for separator in ["+--------------+----+----+----+----+----+----+----¦", "L--------------¦----+----+----+----+----+----+----- ", "Evaluation Only"]):
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
        return rasp_list
    
    # def teach_rasp_data_get(self, schedule_data: list[str])  -> dict[int, dict]:
        

    def rasp_data_get(self, schedule_data: list[str]) -> dict[int, dict]:
        schedule_info: dict[int, dict] = {}

        for lesson_id, line in enumerate(schedule_data, start=1):
            parts = [part.strip() for part in line.split("¦")]

            group_number: str | None = parts[1] or None
            lesson_number_raw: str = parts[2]
            lesson_number: str = lesson_number_raw if lesson_number_raw else "  "

            schedule_info[lesson_id] = {
                "lesson_id": lesson_id,
                "lesson_number": lesson_number,
                "group_number": group_number,
                "subject": parts[3],
                "classroom_number": parts[4],
                "teacher": parts[5],
            }

            self.logger.debug("Урок %s: %s", lesson_id, schedule_info[lesson_id])

        return schedule_info

    async def get_rasp(self, group: int, _get_new: bool = False):
        self.logger.debug(f"Получение расписания для группы: {group}")
        if _get_new is True: 
            await self.get()
        _rasp = self.rasp_parse(group)
        return "\n".join(_rasp)


    @staticmethod
    def days_of_week(date: str):
        date_format = "%d_%m_%Y"
        date_object = datetime.strptime(date, date_format).date()
        days_of_week_ru = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        day_of_week = date_object.weekday()
        days_week = days_of_week_ru[day_of_week]
        return days_week

    async def create_rasp_msg(self, group: int, sec_group: int = None, _get_new: bool = False):
        _rasp_text = await self.get_rasp(group, _get_new)
        day_of_week = str(self.days_of_week(self.date))
        sec_head_text = ''
        _sec_rasp_text = ''
        if sec_group is not None:
            sec_head_text = f"<b>________________________________________</b>\n<b>{self.date.replace('_', '.')}           {day_of_week}           {sec_group}</b>"
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
        if datetime.strptime(next_btn, "%d_%m_%Y").date().weekday() == 6:
            next_btn = (dateObj + timedelta(days=2)).strftime("%d_%m_%Y")
        if datetime.strptime(back_btn, "%d_%m_%Y").date().weekday() == 6:
            back_btn = (dateObj - timedelta(days=2)).strftime("%d_%m_%Y")
        btns = [
            [types.InlineKeyboardButton(text="◀️", callback_data=f"menu:rasp?{(back_btn, False)}"), 
             types.InlineKeyboardButton(text="🔄", callback_data=f"menu:rasp?{(reload_btn, True)}"), 
             types.InlineKeyboardButton(text="▶️", callback_data=f"menu:rasp?{(next_btn, False)}")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


class CheckRasp(Rasp):
    def __init__(self, date: str = None, is_teacher: bool = False) -> None:
        self.is_teacher = is_teacher
        self.logger = create_logger("CheckRasp", level="DEBUG")
        self.date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
        self.logger.debug(f"Инициализация CheckRasp с датой: {self.date}")
        self.db = DB()
    

    async def send_rasp(self, users: list, date: str):
        self.logger.info(f"Отправка расписания для пользователей: {users} и даты: {date}")


    def _create_tasks(self):
        groups = self.db.get_all_usersWgroup()
        tasks = []
        for group in groups.keys():
            users = groups.get(group, [])
            tasks.append([self.send_rasp(users, self.date)])
        return tasks

    async def send_rasp_test(self):
        tasks = self._create_tasks()
        await asyncio.gather(*tasks)

    async def check_rasp_loop(self):
        while True:
            await self.get()
            if self.rasp_exists:
                if os.path.exists(self.base_txt_dir):
                    #TODO: Тут проверка изменилось ли
                    continue
                else:
                    tasks = self._create_tasks()
                    await asyncio.gather(*tasks)
                    


async def main():
    checkrasp = CheckRasp("")



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())