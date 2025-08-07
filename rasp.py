from datetime import datetime, timedelta
import os
import tempfile
from typing import Literal
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
            self.old_base_txt_dir = "data/old_txt"
            self.old_txt_dir = os.path.join(self.old_base_txt_dir, self.txt_filename)
        else:
            self.filename = f"SETKA%20{self.dateWyear}.htm"
            self.txt_filename = f"{self.date}.txt"
            self.base_txt_dir = "data/teach_txt"
            self.txt_dir = os.path.join(self.base_txt_dir, self.txt_filename)
            self.old_base_txt_dir = "data/old_teach_txt"
            self.old_txt_dir = os.path.join(self.old_base_txt_dir, self.txt_filename)

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


    @staticmethod
    def compare_texts(t1, t2):
        import difflib
        t1_lines = [line for line in t1.strip().splitlines()]
        t2_lines = [line for line in t2.strip().splitlines()]
        diff = list(difflib.ndiff(t1_lines, t2_lines))
        result = []
        i = 0
        changes_found = False  # Флаг для отслеживания изменений
        while i < len(diff):
            line = diff[i]
            if line.startswith("  "):
                # Одинаковые строки
                result.append(line[2:])
                i += 1
            elif line.startswith("- "):
                # Удалено
                changes_found = True
                if i + 1 < len(diff) and diff[i + 1].startswith("+ "):
                    # Замена строки
                    result.append(f"<s>{line[2:]}</s>")
                    result.append(f"<b><i>{diff[i + 1][2:]}</i></b>")
                    i += 2
                else:
                    result.append(f"<s>{line[2:]}</s>")
                    i += 1
            elif line.startswith("+ "):
                # Добавлено (если не после удаления — иначе уже обработано как замена)
                changes_found = True
                result.append(f"<b><i>{line[2:]}</i></b>")
                i += 1
            else:
                i += 1
        return "\n".join(result), changes_found


    async def check_diff(self):
        from config import groups
        self.logger.debug("Проверка изменений в расписании")
        checkrasp = CheckRasp(self.date, self.is_teacher)
        db = DB()
        for group in groups:
            old_text = await self.get_rasp(group=group, txt_dir=self.old_txt_dir)
            new_text = await self.get_rasp(group=group, txt_dir=self.txt_dir)
            diff, status = self.compare_texts(old_text, new_text)
            if status is True:
                self.logger.info(f"[DEBUG] DIFF {group} {status} [DEBUG]\n{diff}")
                self.logger.debug(f"Обнаружено изменение в расписании для группы {group}")
                groups = db.get_all_usersBYgroup(group)
                self.logger.debug(diff)
                if "<s>Расписания нету!</s>" in diff: 
                    tasks = checkrasp._create_tasks(mode="new-rasp")
                    await asyncio.gather(*tasks)
                else: 
                    tasks = checkrasp._create_tasks_change(mode="rasp-change", groups=groups, rasp_text=diff)
                    await asyncio.gather(*tasks)
                

    async def convert_htm2txt(self, check_diff: bool = True):
        self.logger.debug("Конвертация HTML в TXT")
        workbook = Workbook(self.temp_file_dir)
        if os.path.exists(self.txt_dir):
            os.remove(self.txt_dir)
            self.logger.debug(f"Файл {self.txt_dir} уже существует, перемещаю в {self.old_txt_dir}")
            workbook.save(self.txt_dir)
            if check_diff: await self.check_diff()
            if os.path.exists(self.old_txt_dir):
                os.remove(self.old_txt_dir)
            os.replace(self.txt_dir, self.old_txt_dir)
            workbook.save(self.txt_dir)
        else:
            workbook.save(self.txt_dir)
        self.logger.debug(f"Файл сохранен как {self.txt_dir}")

    async def get(self, check_diff: bool = True):
        self.logger.debug("Получение данных")
        self.rasp_response = await self._make_request()
        if self.rasp_response is None:
            return
        self.temp_file_dir = os.path.join(tempfile.gettempdir(), f'{self.date}.htm')
        with open(self.temp_file_dir, 'wb') as temp_file:
            self.logger.debug(f"Запись данных во временный файл {self.temp_file_dir}")
            temp_file.write(self.rasp_response)
        self.logger.debug("Данные успешно записаны во временный файл")
        await self.convert_htm2txt(check_diff)

    def rasp_parse(self, group, txt_dir: str = None): 
        rasp_list = []
        rasp_list_done = []
        classes = [f"¦{group}¦"]
        txt_dir = txt_dir if txt_dir is not None else self.txt_dir
        if not os.path.isfile(txt_dir):
            self.logger.debug("Расписание не найдено")
            return ['Расписания нету!']

        with open(txt_dir, "r", encoding="windows-1251") as file:
            content = file.read()

        lines = content.splitlines()
        inside_classes = False  # Флаг, указывающий, что мы находимся внутри уроков из classes

        for line in lines:
            if ("+----+--+--------------+---+---------------+" in line
                    or "L----+--+--------------+---+----------------" in line):
                inside_classes = False
                continue  # Пропустить строку-разделитель

            if "Evaluation Only" in line:
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

    async def get_rasp(self, group: int, _get_new: bool = False, txt_dir: str = None, check_diff: bool = True):
        self.logger.debug(f"Получение расписания для группы: {group}")
        if _get_new is True: 
            await self.get(check_diff)
        _rasp = self.rasp_parse(group, txt_dir)
        return "\n".join(_rasp)


    @staticmethod
    def days_of_week(date: str):
        date_format = "%d_%m_%Y"
        date_object = datetime.strptime(date, date_format).date()
        days_of_week_ru = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        day_of_week = date_object.weekday()
        days_week = days_of_week_ru[day_of_week]
        return days_week

    from typing import Literal
    def gen_head_text(self, group: str, mode: Literal["rasp-change", 'new-rasp', "None"], rasp_mode: Literal["main", "sec"]):
        day_of_week = str(self.days_of_week(self.date))
        date_obj = datetime.strptime(self.date, "%d_%m_%Y")
        day = date_obj.day
        month = date_obj.month
        if (month == 12 and day >= 28) or (month == 1 and day <= 3):
            date_str = self.date.replace('_', '.')
        else:
            date_str = date_obj.strftime("%d.%m")
        head = {
            "rasp-change": f"🔄 <b>Расписание изменилось!</b>",
            'new-rasp': f"📢 <b>Вышло новое расписание!</b>",
            "None": ''
        }
        footer = {
            "main": f"<b>{date_str}           {day_of_week}           {group}</b>",
            "sec": f"<b>________________________________________</b>\n<b>{date_str}           {day_of_week}           {group}</b>",
        }
        if mode != "None":
            return f'{head.get(mode)}\n{footer.get(rasp_mode)}'
        else:
            return f'{footer.get(rasp_mode)}'

    async def create_rasp_msg(self, group: int, sec_group: int = None, _get_new: bool = False):
        _rasp_text = await self.get_rasp(group, _get_new)
        sec_head_text = ''
        _sec_rasp_text = ''
        if sec_group is not None:
            sec_head_text = self.gen_head_text(sec_group, mode='None', rasp_mode="sec")
            _sec_rasp_text += await self.get_rasp(sec_group, _get_new)
        
        head_text = self.gen_head_text(group, mode='None', rasp_mode="main")
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
        super().__init__(self.date, self.is_teacher)

    
    async def send_rasp(self, user: list, date: str, group: int, mode: Literal['new-rasp', 'rasp-change'], rasp_text: str = None):
        self.logger.info(f"Отправка расписания для пользователя: {user} и даты: {date}")
        if rasp_text is None: rasp_text = await self.get_rasp(group, _get_new=False, check_diff=False)
        text = f"{self.gen_head_text(group, mode=mode, rasp_mode='main')}\n\n{rasp_text}"
        try: 
            msg = await bot.send_message(
                chat_id=user,
                text=text
            )
            self.logger.debug(f"Расписание успешно отправлено в {user}, номер группы: {group}")
            return True
        except Exception as e:
            self.logger.debug(f"Произошла ошибка при отправке расписания в {user}, номер группы: {group}. e={str(e)}")
            if str(e) == "Telegram server says - Forbidden: bot was blocked by the user":
                db = DB()
                await db.delete(user_id=user)
                return "bot_blocked"
            elif str(e) == "Telegram server says - Bad Request: not enough rights to manage pinned messages in the chat":
                await msg.reply("❌ Не удалось закрепить новое расписание\n\n🔧 Для закрепления сообщений назначьте меня администратором с правами:\n• Закрепление сообщений\n• Удаление сообщений")
                return True
            else:
                return False
    
    def _create_tasks(self, mode: Literal['new-rasp', 'rasp-change']):
        groups = self.db.get_all_usersWgroup()
        tasks = []
        for group, users in groups.items():
            if users != []:
                for user in users:
                    tasks.append(self.send_rasp(user, self.date, group, mode))
        return tasks

    def _create_tasks_change(self, mode: Literal['new-rasp', 'rasp-change'], groups: dict = {}, rasp_text: str = None):
        tasks = []
        for group, users in groups.items():
            if users != []:
                for user in users:
                    tasks.append(self.send_rasp(user, self.date, group, mode, rasp_text))
        return tasks

    async def send_rasp_test(self):
        tasks = self._create_tasks(mode="new-rasp")
        await asyncio.gather(*tasks)

    async def check_rasp_loop(self):
        while True:
            await self.get()
            if self.rasp_exists:
                if os.path.exists(self.base_txt_dir):
                    #TODO: Тут проверка изменилось ли
                    continue
                else:
                    tasks = self._create_tasks(mode="new-rasp")
                    await asyncio.gather(*tasks)
                    


async def main():
    checkrasp = CheckRasp("31_10_2024")
    await checkrasp.send_rasp_test()



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())