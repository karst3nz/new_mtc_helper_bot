from datetime import datetime, timedelta
import logging
import os
import tempfile
from typing import Literal
import asyncio
import aiohttp
from aspose.cells import Workbook
from db import DB
from log import create_logger
from config import *


class Rasp:
    def __init__(self, date: str = None, is_teacher: bool = False) -> None:
        self.is_teacher = is_teacher
        self.logger = create_logger("Rasp")
        self.date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
        self.logger.info(f"Инициализация Rasp с датой: {self.date}")
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
        try:
            self.session = aiohttp.ClientSession(headers=self.headers)
        except Exception as e:
            self.logger.error(f"Не удалось создать сессию aiohttp: {e}")
            raise

    async def close_session(self):  
        self.logger.debug("Закрытие сессии")
        try:
            if hasattr(self, "session"):
                await self.session.close()
        except Exception as e:
            self.logger.warning(f"Исключение при закрытии сессии: {e}")

    async def _make_request(self):
        await self.run_session()
        self.logger.info(f"Отправка запроса на {self.url}")
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with self.session.get(self.url, timeout=timeout) as response:
                status = response.status
                if 400 <= status < 500:
                    self.logger.warning(f"HTTP {status} при запросе {self.url}")
                    self.rasp_exists = False
                    return None
                if status >= 500:
                    self.logger.error(f"HTTP {status} (серверная ошибка) при запросе {self.url}")
                    self.rasp_exists = False
                    return None
                r = await response.read()
                self.logger.info(f"Запрос выполнен успешно, статус: {status}, получено байт: {len(r)}")
                self.rasp_exists = True
                return r
        except aiohttp.ClientError as e:
            self.logger.error(f"Сетевая ошибка при запросе {self.url}: {e}")
            self.rasp_exists = False
            return None
        except asyncio.TimeoutError:
            self.logger.error(f"Таймаут при запросе {self.url}")
            self.rasp_exists = False
            return None
        except Exception as e:
            self.logger.error(f"Необработанное исключение при запросе {self.url}: {e}")
            self.rasp_exists = False
            return None
        finally:
            await self.close_session()


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
        self.logger.info("Проверка изменений в расписании")
        checkrasp = CheckRasp(self.date, self.is_teacher)
        db = DB()
        # Сброс состояния дедупликации перед новым проходом сравнения
        checkrasp._sent_users.clear()
        checkrasp._broadcast_sent = False
        for group in groups:
            try:
                old_text = await self.get_rasp(group=group, txt_dir=self.old_txt_dir)
                new_text = await self.get_rasp(group=group, txt_dir=self.txt_dir)
                diff, status = self.compare_texts(old_text, new_text)
                self.logger.debug(f"Группа {group}: изменения обнаружены={status}")
                if status is True:
                    # # Причина выбора режима отправки
                    # if "<s>Расписания нету!</s>" in diff:
                    #     if not checkrasp._broadcast_sent:
                    #         self.logger.info(f"Группа {group}: новое расписание (причина: исчезла строка 'Расписания нету!'). Запускаю одноразовую рассылку new-rasp")
                    #         tasks = checkrasp._create_tasks(mode="new-rasp")
                    #         checkrasp._broadcast_sent = True
                    #         await asyncio.gather(*tasks)
                    #     else:
                    #         self.logger.debug("Одноразовая рассылка new-rasp уже выполнена в этом проходе — пропускаю")
                    # else:
                    self.logger.info(f"Группа {group}: изменение расписания (причина: найден diff). Длина diff: {len(diff)} символов")
                    groups = db.get_all_usersBYgroup(group)
                    tasks = checkrasp._create_tasks_change(mode="rasp-change", groups=groups, rasp_text=diff)
                    await asyncio.gather(*tasks)
            except Exception as e:
                self.logger.error(f"Ошибка при проверке изменений для группы {group}: {e}")
                continue
                

    async def convert_htm2txt(self, check_diff: bool = True):
        self.logger.info("Конвертация HTML в TXT")
        try:
            workbook = Workbook(self.temp_file_dir)
        except Exception as e:
            self.logger.error(f"Не удалось открыть временный файл как Workbook: {self.temp_file_dir}, ошибка: {e}")
            return
        try:
            if os.path.exists(self.txt_dir):
                self.logger.info(f"Файл {self.txt_dir} уже существует, перемещаю в {self.old_txt_dir}")
                # Перезапись текущего как текущий, затем сравнение и перенос в old
                os.remove(self.txt_dir)
                workbook.save(self.txt_dir)
                if check_diff:
                    await self.check_diff()
                if os.path.exists(self.old_txt_dir):
                    try:
                        os.remove(self.old_txt_dir)
                    except Exception as e:
                        self.logger.warning(f"Не удалось удалить старый файл {self.old_txt_dir}: {e}")
                os.replace(self.txt_dir, self.old_txt_dir)
                workbook.save(self.txt_dir)
            else:
                workbook.save(self.txt_dir)
                workbook.save(self.old_txt_dir)
                checkrasp = CheckRasp(self.date, self.is_teacher)
                if not checkrasp._broadcast_sent:
                    self.logger.info(f"Новое расписание (причина: записан файл {self.txt_dir}). Запускаю одноразовую рассылку new-rasp")
                    tasks = checkrasp._create_tasks(mode="new-rasp")
                    checkrasp._broadcast_sent = True
                    await asyncio.gather(*tasks)
                else:
                    self.logger.debug("Одноразовая рассылка new-rasp уже выполнена в этом проходе — пропускаю")
            self.logger.info(f"Файл сохранен как {self.txt_dir}")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении TXT {self.txt_dir}: {e}")

    async def get(self, check_diff: bool = True):
        self.logger.info("Получение данных")
        self.rasp_response = await self._make_request()
        if self.rasp_response is None:
            self.logger.warning("Данные не получены: ответ пустой или произошла ошибка")
            return
        self.temp_file_dir = os.path.join(tempfile.gettempdir(), f'{self.date}.htm')
        try:
            with open(self.temp_file_dir, 'wb') as temp_file:
                self.logger.info(f"Запись данных во временный файл {self.temp_file_dir}")
                temp_file.write(self.rasp_response)
            self.logger.info("Данные успешно записаны во временный файл")
        except Exception as e:
            self.logger.error(f"Не удалось записать временный файл {self.temp_file_dir}: {e}")
            return
        await self.convert_htm2txt(check_diff)

    def rasp_parse(self, group, txt_dir: str = None): 
        rasp_list = []
        rasp_list_done = []
        classes = [f"¦{group}¦"]
        txt_dir = txt_dir if txt_dir is not None else self.txt_dir
        if not os.path.isfile(txt_dir):
            self.logger.warning("Расписание не найдено: файл отсутствует %s", txt_dir)
            return ['Расписания нету!']

        try:
            with open(txt_dir, "r", encoding="windows-1251") as file:
                content = file.read()
        except UnicodeDecodeError as e:
            self.logger.error(f"Ошибка декодирования файла {txt_dir}: {e}")
            return ['Расписания нету!']
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла {txt_dir}: {e}")
            return ['Расписания нету!']

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
                self.logger.debug(f"Найдена секция группы {group} в файле")
                rasp_list.append(line)
                inside_classes = True

        if rasp_list:
            rasp_info = self.rasp_data_get(rasp_list)
            if isinstance(rasp_info, dict):
                try:
                    lesson_number_to_lookup = max(item['lesson_id'] for item in rasp_info.values() if item['lesson_id'])
                    lesson_id = min(item['lesson_id'] for item in rasp_info.values() if item['lesson_id']) - 1
                except ValueError:
                    self.logger.warning("Не удалось определить диапазон уроков для группы %s", group)
                    return ['Расписания нету!']
                
                while lesson_id < lesson_number_to_lookup:
                    lesson_id += 1
                    rasp_info_process = rasp_info.get(lesson_id)
                    if rasp_info_process:
                        rasp_list_done.append(
                            f"{rasp_info_process['lesson_number']} | {rasp_info_process['subject']} "
                            f"| {rasp_info_process['classroom_number']} | {rasp_info_process['teacher']}"
                        )

            return rasp_list_done

        return ['Расписания нету!']


    def rasp_data_get(self, schedule_data: list[str]) -> dict[int, dict]:
        schedule_info: dict[int, dict] = {}

        for lesson_id, line in enumerate(schedule_data, start=1):
            parts = [part.strip() for part in line.split("¦")]
            if len(parts) < 6:
                self.logger.warning(f"Строка расписания имеет некорректный формат (мало столбцов): {line}")
                continue

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


        return schedule_info

    async def get_rasp(self, group: int, _get_new: bool = False, txt_dir: str = None, check_diff: bool = True):
        self.logger.debug(f"Получение расписания для группы: {group}")
        if _get_new is True: 
            await self.get(check_diff)
            if not self.rasp_exists:
                self.logger.warning("Не удалось обновить расписание — источник недоступен или ошибка загрузки")
        _rasp = self.rasp_parse(group, txt_dir)
        result = "\n".join(_rasp)
        self.logger.debug(f"Длина итогового текста расписания для группы {group}: {len(result)} символов")
        return result


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
            self.logger.debug(f"Добавление второго расписания для группы {sec_group}")
            sec_head_text = self.gen_head_text(sec_group, mode='None', rasp_mode="sec")
            _sec_rasp_text += await self.get_rasp(sec_group, _get_new)
        
        head_text = self.gen_head_text(group, mode='None', rasp_mode="main")
        if sec_head_text != '' and _sec_rasp_text != '':
            text = f"""
{head_text}

{_rasp_text}
{sec_head_text}

{_sec_rasp_text}
"""
        else:
            text = f"""
{head_text}

{_rasp_text}
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
        self.logger.debug("Сформировано сообщение расписания и кнопки навигации")
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


class CheckRasp(Rasp):
    def __init__(self, date: str = None, is_teacher: bool = False) -> None:
        self.is_teacher = is_teacher
        self.logger = create_logger("CheckRasp")
        self.date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
        self.logger.info(f"Инициализация CheckRasp с датой: {self.date}")
        self.db = DB()
        # Дедупликация отправок
        self._sent_users: set[int] = set()
        self._broadcast_sent: bool = False
        super().__init__(self.date, self.is_teacher)

    
    async def send_rasp(self, user: list, date: str, group: int, mode: Literal['new-rasp', 'rasp-change'], rasp_text: str = None):
        db = DB()
        self.logger.info(f"Отправка расписания для пользователя: {user} и даты: {date}")
        if rasp_text is None:
            self.logger.debug(f"Формирование текста для отправки (lazy fetch), группа {group}, mode={mode}")
            rasp_text = await self.get_rasp(group, _get_new=False, check_diff=False)
        # Проверка наличия контента для отправки
        if not rasp_text or rasp_text.strip() == '' or rasp_text.strip() == 'Расписания нету!':
            self.logger.warning(f"Отправка пропущена: нет содержимого расписания для группы {group} (mode={mode}). Причина: пустой текст или 'Расписания нету!'")
            return False
        preview = (rasp_text[:120] + '…') if len(rasp_text) > 120 else rasp_text
        self.logger.debug(f"Подготовлен текст для отправки (mode={mode}, группа={group}). Превью: {preview}")
        text = f"{self.gen_head_text(group, mode=mode, rasp_mode='main')}\n\n{rasp_text}"
        userDC = db.get_user_dataclass(user)
        if "newRasp" in userDC.show_missed_hours_mode:
            text += f"\n\n⏰ У тебя сейчас <b>{userDC.missed_hours}</b> пропущенных часов."
        try: 
            msg = await bot.send_message(
                chat_id=user,
                text=text
            )
            self.logger.info(f"Расписание успешно отправлено в {user}, номер группы: {group}")
            return True
        except Exception as e:
            self.logger.error(f"Произошла ошибка при отправке расписания в {user}, номер группы: {group}. e={str(e)}")
            if str(e) == "Telegram server says - Forbidden: bot was blocked by the user":
                await db.delete(user_id=user)
                self.logger.warning(f"Пользователь {user} заблокировал бота. Удалён из базы.")
                return "bot_blocked"
            elif str(e) == "Telegram server says - Bad Request: not enough rights to manage pinned messages in the chat":
                await msg.reply("❌ Не удалось закрепить новое расписание\n\n🔧 Для закрепления сообщений назначьте меня администратором с правами:\n• Закрепление сообщений\n• Удаление сообщений")
                self.logger.warning(f"Недостаточно прав для закрепления сообщения у пользователя {user}")
                return True
            else:
                return False
    
    def _create_tasks(self, mode: Literal['new-rasp', 'rasp-change']):
        if SEND_RASP == "0":
            self.logger.warning("Рассылка отключена (SEND_RASP=0). Задачи не будут сформированы.")
            return []
        groups = self.db.get_all_usersWgroup()
        tasks = []
        for group, users in groups.items():
            if users != []:
                for user in users:
                    if user in self._sent_users:
                        self.logger.debug(f"Пропуск дубликата: пользователь {user} уже в очереди отправки")
                        continue
                    self._sent_users.add(user)
                    tasks.append(self.send_rasp(user, self.date, group, mode))
        self.logger.debug(f"Создано задач на отправку: {len(tasks)}")
        return tasks

    def _create_tasks_change(self, mode: Literal['new-rasp', 'rasp-change'], groups: dict = {}, rasp_text: str = None):
        if SEND_RASP == "0":
            self.logger.warning("Рассылка отключена (SEND_RASP=0). Задачи не будут сформированы.")
            return []
        tasks = []
        for group, users in groups.items():
            if users != []:
                for user in users:
                    if user in self._sent_users:
                        self.logger.debug(f"Пропуск дубликата: пользователь {user} уже в очереди отправки (изменения)")
                        continue
                    self._sent_users.add(user)
                    tasks.append(self.send_rasp(user, self.date, group, mode, rasp_text))
        self.logger.debug(f"Создано задач на отправку (изменения): {len(tasks)}")
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
                    self.logger.debug("Базовая директория TXT существует, продолжаю цикл без отправки")
                    continue
                else:
                    tasks = self._create_tasks(mode="new-rasp")
                    self.logger.info("Директория с TXT не найдена — рассылаю новое расписание")
                    await asyncio.gather(*tasks)
                    


async def main():
    checkrasp = CheckRasp("01_09_2025")
    await checkrasp.send_rasp_test()



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())