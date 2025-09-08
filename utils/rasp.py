from datetime import datetime, timedelta
import logging
import os
import tempfile
from typing import Literal
import asyncio
import aiohttp
from aspose.cells import Workbook
from utils.db import DB
from utils.log import create_logger
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
        import re
        
        def normalize_for_comparison(line):
            """Нормализует строку для сравнения, убирая все пробелы"""
            # Убираем все пробелы для сравнения
            return re.sub(r'\s+', '', line)
        
        def normalize_for_display(line):
            """Нормализует строку для отображения, убирая лишние пробелы"""
            # Убираем пробелы в начале и конце
            line = line.strip()
            # Заменяем множественные пробелы на один
            line = re.sub(r'\s+', ' ', line)
            return line
        
        # Получаем оригинальные строки
        t1_lines = [line for line in t1.strip().splitlines()]
        t2_lines = [line for line in t2.strip().splitlines()]
        
        # Нормализуем для сравнения (убираем все пробелы)
        t1_normalized = [normalize_for_comparison(line) for line in t1_lines]
        t2_normalized = [normalize_for_comparison(line) for line in t2_lines]
        
        # Сравниваем нормализованные строки
        diff = list(difflib.ndiff(t1_normalized, t2_normalized))
        result = []
        i = 0
        changes_found = False  # Флаг для отслеживания изменений
        
        while i < len(diff):
            line = diff[i]
            if line.startswith("  "):
                # Одинаковые строки - добавляем оригинальную строку
                line_index = len([x for x in diff[:i] if x.startswith("  ") or x.startswith("- ")])
                if line_index < len(t1_lines):
                    result.append(normalize_for_display(t1_lines[line_index]))
                i += 1
            elif line.startswith("- "):
                # Удалено
                if i + 1 < len(diff) and diff[i + 1].startswith("+ "):
                    # Замена строки
                    old_index = len([x for x in diff[:i] if x.startswith("  ") or x.startswith("- ")])
                    new_index = len([x for x in diff[:i+1] if x.startswith("  ") or x.startswith("+ ")])
                    
                    if old_index < len(t1_lines) and new_index < len(t2_lines):
                        old_line = normalize_for_display(t1_lines[old_index])
                        new_line = normalize_for_display(t2_lines[new_index])
                        
                        # Если строки отличаются только пробелами, игнорируем изменение
                        if normalize_for_comparison(old_line) == normalize_for_comparison(new_line):
                            result.append(old_line)  # Оставляем оригинальную строку
                            i += 2
                            continue
                        
                        # Реальное изменение содержимого
                        changes_found = True
                        result.append(f"<s>{old_line}</s>")
                        result.append(f"<b><i>{new_line}</i></b>")
                    i += 2
                else:
                    # Удаление строки
                    old_index = len([x for x in diff[:i] if x.startswith("  ") or x.startswith("- ")])
                    if old_index < len(t1_lines):
                        changes_found = True
                        result.append(f"<s>{normalize_for_display(t1_lines[old_index])}</s>")
                    i += 1
            elif line.startswith("+ "):
                # Добавлено (если не после удаления — иначе уже обработано как замена)
                new_index = len([x for x in diff[:i] if x.startswith("  ") or x.startswith("+ ")])
                if new_index < len(t2_lines):
                    changes_found = True
                    result.append(f"<b><i>{normalize_for_display(t2_lines[new_index])}</i></b>")
                i += 1
            else:
                i += 1
        
        return "\n".join(result), changes_found


    async def check_diff(self):
        from config import groups
        self.logger.info(f"[CHECK_DIFF] Начало проверки изменений | Дата: {self.date} | Групп для проверки: {len(groups)}")
        checkrasp = CheckRasp(self.date, self.is_teacher)
        db = DB()
        
        # Сброс состояния дедупликации перед новым проходом сравнения
        checkrasp._sent_users.clear()
        checkrasp._broadcast_sent = False
        self.logger.debug(f"[CHECK_DIFF] Состояние дедупликации сброшено | Отправленных пользователей: {len(checkrasp._sent_users)} | Broadcast sent: {checkrasp._broadcast_sent}")
        
        groups_with_changes = 0
        total_diff_length = 0
        
        for group in groups:
            try:
                self.logger.debug(f"[CHECK_DIFF] Проверка группы | Группа: {group}")
                old_text = await self.get_rasp(group=group, txt_dir=self.old_txt_dir)
                new_text = await self.get_rasp(group=group, txt_dir=self.txt_dir)
                
                old_length = len(old_text)
                new_length = len(new_text)
                self.logger.debug(f"[CHECK_DIFF] Получены тексты | Группа: {group} | Старый текст: {old_length} символов | Новый текст: {new_length} символов")
                
                diff, status = self.compare_texts(old_text, new_text)
                diff_length = len(diff)
                
                self.logger.debug(f"[CHECK_DIFF] Сравнение завершено | Группа: {group} | Изменения обнаружены: {status} | Длина diff: {diff_length} символов")
                
                if status is True:
                    groups_with_changes += 1
                    total_diff_length += diff_length
                    self.logger.info(f"[CHECK_DIFF] Изменения найдены | Группа: {group} | Длина diff: {diff_length} символов | Причина: найден diff")
                    
                    # Отправка пользователям
                    user_groups = db.get_all_usersBYgroup(group)
                    if user_groups:
                        self.logger.info(f"[CHECK_DIFF] Отправка пользователям | Группа: {group} | Пользователей: {len(user_groups)}")
                        tasks = checkrasp._create_tasks_change(mode="rasp-change", groups=user_groups, rasp_text=diff)
                        if tasks:
                            await asyncio.gather(*tasks)
                            self.logger.info(f"[CHECK_DIFF] Отправка пользователям завершена | Группа: {group} | Задач выполнено: {len(tasks)}")
                        else:
                            self.logger.warning(f"[CHECK_DIFF] Нет задач для отправки пользователям | Группа: {group}")
                    else:
                        self.logger.debug(f"[CHECK_DIFF] Нет пользователей для отправки | Группа: {group}")
                    
                    # Отправка в группы
                    tg_groups = db.get_all_TGgroupsBYgroup(group)
                    if tg_groups:
                        self.logger.info(f"[CHECK_DIFF] Отправка в группы | Группа: {group} | TG групп: {len(tg_groups)}")
                        tasks = checkrasp._create_tasks_change(mode="rasp-change", groups=tg_groups, rasp_text=diff)
                        if tasks:
                            await asyncio.gather(*tasks)
                            self.logger.info(f"[CHECK_DIFF] Отправка в группы завершена | Группа: {group} | Задач выполнено: {len(tasks)}")
                        else:
                            self.logger.warning(f"[CHECK_DIFF] Нет задач для отправки в группы | Группа: {group}")
                    else:
                        self.logger.debug(f"[CHECK_DIFF] Нет TG групп для отправки | Группа: {group}")
                else:
                    self.logger.debug(f"[CHECK_DIFF] Изменений нет | Группа: {group} | Длина diff: {diff_length} символов")
                    
            except Exception as e:
                self.logger.error(f"[CHECK_DIFF] Ошибка проверки группы | Группа: {group} | Ошибка: {str(e)} | Тип: {type(e).__name__}")
                continue
        
        self.logger.info(f"[CHECK_DIFF] Проверка завершена | Всего групп: {len(groups)} | Групп с изменениями: {groups_with_changes} | Общая длина diff: {total_diff_length} символов")
                

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
                db = DB()
                if not checkrasp._broadcast_sent:
                    self.logger.info(f"[NEW_RASP_BROADCAST] Новое расписание обнаружено | Файл: {self.txt_dir} | Запуск одноразовой рассылки new-rasp")
                    checkrasp._broadcast_sent = False

                    # Рассылка пользователям
                    user_groups = db.get_all_usersWgroup()
                    if user_groups:
                        total_users = sum(len(users) for users in user_groups.values() if users)
                        self.logger.info(f"[NEW_RASP_BROADCAST] Рассылка пользователям | Групп: {len(user_groups)} | Всего пользователей: {total_users}")
                        tasks = checkrasp._create_tasks(mode="new-rasp", groups=user_groups)
                        if tasks:
                            self.logger.debug(f"[NEW_RASP_BROADCAST] Выполнение задач рассылки пользователям | Задач: {len(tasks)}")
                            checkrasp._broadcast_sent = True
                            try:
                                await asyncio.gather(*tasks)
                                self.logger.info(f"[NEW_RASP_BROADCAST] Рассылка пользователям завершена успешно | Выполнено задач: {len(tasks)}")
                            except Exception as e:
                                self.logger.error(f"[NEW_RASP_BROADCAST] Ошибка рассылки пользователям | Ошибка: {str(e)} | Тип: {type(e).__name__}")
                            finally:
                                checkrasp._broadcast_sent = False
                        else:
                            self.logger.warning(f"[NEW_RASP_BROADCAST] Нет задач для рассылки пользователям")
                    else:
                        self.logger.warning(f"[NEW_RASP_BROADCAST] Нет пользователей для рассылки")

                    # Рассылка в группы
                    tg_groups = db.get_all_TGgroupsWgroup()
                    if tg_groups:
                        total_tg_groups = sum(len(users) for users in tg_groups.values() if users)
                        self.logger.info(f"[NEW_RASP_BROADCAST] Рассылка в группы | Групп: {len(tg_groups)} | Всего получателей: {total_tg_groups}")
                        tasks = checkrasp._create_tasks(mode="new-rasp", groups=tg_groups)
                        if tasks:
                            self.logger.debug(f"[NEW_RASP_BROADCAST] Выполнение задач рассылки в группы | Задач: {len(tasks)}")
                            checkrasp._broadcast_sent = True
                            try:
                                await asyncio.gather(*tasks)
                                self.logger.info(f"[NEW_RASP_BROADCAST] Рассылка в группы завершена успешно | Выполнено задач: {len(tasks)}")
                            except Exception as e:
                                self.logger.error(f"[NEW_RASP_BROADCAST] Ошибка рассылки в группы | Ошибка: {str(e)} | Тип: {type(e).__name__}")
                            finally:
                                checkrasp._broadcast_sent = False
                        else:
                            self.logger.warning(f"[NEW_RASP_BROADCAST] Нет задач для рассылки в группы")
                    else:
                        self.logger.warning(f"[NEW_RASP_BROADCAST] Нет групп для рассылки")
                else:
                    self.logger.debug(f"[NEW_RASP_BROADCAST] Пропуск | Одноразовая рассылка new-rasp уже выполнена в этом проходе")
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
        self.logger.info(f"[SEND_RASP] Начало отправки | Пользователь: {user} | Дата: {date} | Группа: {group} | Режим: {mode}")
        
        if rasp_text is None:
            self.logger.debug(f"[SEND_RASP] Lazy fetch текста | Группа: {group} | Режим: {mode}")
            rasp_text = await self.get_rasp(group, _get_new=False, check_diff=False)
        
        # Проверка наличия контента для отправки
        if not rasp_text or rasp_text.strip() == '' or rasp_text.strip() == 'Расписания нету!':
            self.logger.warning(f"[SEND_RASP] Отправка пропущена | Пользователь: {user} | Группа: {group} | Режим: {mode} | Причина: пустой текст или 'Расписания нету!'")
            return False
        
        # Логирование статистики контента
        content_length = len(rasp_text)
        preview = (rasp_text[:120] + '…') if content_length > 120 else rasp_text
        self.logger.debug(f"[SEND_RASP] Подготовка контента | Пользователь: {user} | Группа: {group} | Режим: {mode} | Длина: {content_length} символов | Превью: {preview}")
        
        # Формирование текста сообщения
        text = f"{self.gen_head_text(group, mode=mode, rasp_mode='main')}\n\n{rasp_text}"
        userDC = db.get_user_dataclass(user)
        groupDC = db.get_TGgroup_dataclass(user)
        # Добавление информации о пропущенных часах
        missed_hours_added = False
        if "newRasp" in str(userDC.show_missed_hours_mode):
            text += f"\n\n⏰ У тебя сейчас <b>{userDC.missed_hours}</b> пропущенных часов."
            missed_hours_added = True
            self.logger.debug(f"[SEND_RASP] Добавлена информация о пропущенных часах | Пользователь: {user} | Часов: {userDC.missed_hours}")
        
        final_length = len(text)
        self.logger.debug(f"[SEND_RASP] Финальная подготовка | Пользователь: {user} | Группа: {group} | Режим: {mode} | Итоговая длина: {final_length} символов | Пропущенные часы: {missed_hours_added}")
        
        try: 
            msg = await bot.send_message(
                chat_id=user,
                text=text
            )
            self.logger.info(f"[SEND_RASP] Успешная отправка | Пользователь: {user} | Группа: {group} | Режим: {mode} | Длина сообщения: {final_length} символов | ID сообщения: {msg.message_id}")
            if bool(groupDC.pin_new_rasp) == True: # даже если groupDC.pin_new_rasp == None выведет False, bool(None) == False
                self.logger.info(f"[SEND_RASP] Закрепление отправленного сообщения в чате | Пользователь: {user} | Группа: {group} | ID сообщения: {msg.message_id}")
                try:
                    await bot.pin_chat_message(
                        chat_id=user,
                        message_id=msg.message_id
                    )
                    self.logger.info(f"[SEND_RASP] Успешно закрепил отправленное сообщение в чате | Пользователь: {user} | Группа: {group} | ID сообщения: {msg.message_id}")
                except Exception as e:
                    error_msg = str(e)
                    if error_msg == "Telegram server says - Bad Request: not enough rights to manage pinned messages in the chat":
                        btns = [
                            [types.InlineKeyboardButton(text="Проверить права", callback_data="check_pin_rights")]
                        ]
                        await msg.reply("❌ Не удалось закрепить новое расписание\n\n🔧 Для закрепления сообщений назначьте меня администратором с правами:\n• Закрепление сообщений\n• Удаление сообщений", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))
                        self.logger.warning(f"[SEND_RASP] Недостаточно прав для закрепления | Пользователь: {user} | Группа: {group}")
                    else:
                        self.logger.error(f"[SEND_RASP] Необработанная ошибка | Пользователь: {user} | Группа: {group} | Режим: {mode} | Тип ошибки: {type(e).__name__} | Сообщение: {error_msg}")
                        return False            
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"[SEND_RASP] Ошибка отправки | Пользователь: {user} | Группа: {group} | Режим: {mode} | Ошибка: {error_msg}")
            
            if error_msg == "Telegram server says - Forbidden: bot was blocked by the user":
                await db.delete(user_id=user, table=db.users_table)
                self.logger.warning(f"[SEND_RASP] Пользователь заблокировал бота | Пользователь: {user} | Действие: удален из базы")
                return "bot_blocked"
                
            elif error_msg == "Telegram server says - Bad Request: chat not found":
                await db.delete(user_id=user, table=db.users_table)
                self.logger.warning(f"[SEND_RASP] У бота нету чата с пользователем | Пользователь: {user} | Действие: удален из базы")
                return False
            else:
                self.logger.error(f"[SEND_RASP] Необработанная ошибка | Пользователь: {user} | Группа: {group} | Режим: {mode} | Тип ошибки: {type(e).__name__} | Сообщение: {error_msg}")
                return False
    
    
    def _create_tasks(self, mode: Literal['new-rasp', 'rasp-change'], groups: dict = {}):
        if SEND_RASP == "0":
            self.logger.warning("[CREATE_TASKS] Рассылка отключена | SEND_RASP=0 | Задачи не будут сформированы")
            return []
        
        total_users = sum(len(users) for users in groups.values() if users)
        self.logger.info(f"[CREATE_TASKS] Начало создания задач | Режим: {mode} | Групп: {len(groups)} | Всего пользователей: {total_users}")
        
        tasks = []
        skipped_duplicates = 0
        
        for group, users in groups.items():
            if not users:
                continue
                
            self.logger.debug(f"[CREATE_TASKS] Обработка группы | Группа: {group} | Пользователей: {len(users)}")
            
            for user in users:
                if user in self._sent_users:
                    skipped_duplicates += 1
                    self.logger.debug(f"[CREATE_TASKS] Пропуск дубликата | Пользователь: {user} | Группа: {group} | Причина: уже в очереди отправки")
                    continue
                    
                self._sent_users.add(user)
                tasks.append(self.send_rasp(user, self.date, group, mode))
        
        self.logger.info(f"[CREATE_TASKS] Задачи созданы | Режим: {mode} | Создано задач: {len(tasks)} | Пропущено дубликатов: {skipped_duplicates} | Всего пользователей: {total_users}")
        return tasks

    def _create_tasks_change(self, mode: Literal['new-rasp', 'rasp-change'], groups: dict = {}, rasp_text: str = None):
        if SEND_RASP == "0":
            self.logger.warning("[CREATE_TASKS_CHANGE] Рассылка отключена | SEND_RASP=0 | Задачи не будут сформированы")
            return []
        
        total_users = sum(len(users) for users in groups.values() if users)
        diff_length = len(rasp_text) if rasp_text else 0
        self.logger.info(f"[CREATE_TASKS_CHANGE] Начало создания задач изменений | Режим: {mode} | Групп: {len(groups)} | Всего пользователей: {total_users} | Длина diff: {diff_length} символов")
        
        tasks = []
        skipped_duplicates = 0
        
        for group, users in groups.items():
            if not users:
                continue
                
            self.logger.debug(f"[CREATE_TASKS_CHANGE] Обработка группы изменений | Группа: {group} | Пользователей: {len(users)}")
            
            for user in users:
                if user in self._sent_users:
                    skipped_duplicates += 1
                    self.logger.debug(f"[CREATE_TASKS_CHANGE] Пропуск дубликата | Пользователь: {user} | Группа: {group} | Причина: уже в очереди отправки изменений")
                    continue
                    
                self._sent_users.add(user)
                tasks.append(self.send_rasp(user, self.date, group, mode, rasp_text))
        
        self.logger.info(f"[CREATE_TASKS_CHANGE] Задачи изменений созданы | Режим: {mode} | Создано задач: {len(tasks)} | Пропущено дубликатов: {skipped_duplicates} | Всего пользователей: {total_users} | Длина diff: {diff_length} символов")
        return tasks

    async def send_rasp_test(self):
        tasks = self._create_tasks(mode="new-rasp")
        await asyncio.gather(*tasks)

    async def check_rasp_loop(self):
        loop_count = 0
        self.logger.info(f"[CHECK_RASP_LOOP] Запуск цикла проверки расписания | Дата: {self.date}")
        
        while True:
            loop_count += 1
            self.logger.debug(f"[CHECK_RASP_LOOP] Итерация #{loop_count} | Дата: {self.date}")
            
            await self.get()
            
            if self.rasp_exists:
                self.logger.debug(f"[CHECK_RASP_LOOP] Расписание получено | Итерация: #{loop_count} | Дата: {self.date}")
                
                if os.path.exists(self.base_txt_dir):
                    self.logger.debug(f"[CHECK_RASP_LOOP] Базовая директория TXT существует | Итерация: #{loop_count} | Директория: {self.base_txt_dir} | Продолжение цикла без отправки")
                    continue
                else:
                    self.logger.info(f"[CHECK_RASP_LOOP] Директория с TXT не найдена | Итерация: #{loop_count} | Запуск рассылки нового расписания")
                    tasks = self._create_tasks(mode="new-rasp")
                    
                    if tasks:
                        self.logger.info(f"[CHECK_RASP_LOOP] Выполнение рассылки | Итерация: #{loop_count} | Задач: {len(tasks)}")
                        try:
                            await asyncio.gather(*tasks)
                            self.logger.info(f"[CHECK_RASP_LOOP] Рассылка завершена успешно | Итерация: #{loop_count} | Выполнено задач: {len(tasks)}")
                        except Exception as e:
                            self.logger.error(f"[CHECK_RASP_LOOP] Ошибка рассылки | Итерация: #{loop_count} | Ошибка: {str(e)} | Тип: {type(e).__name__}")
                    else:
                        self.logger.warning(f"[CHECK_RASP_LOOP] Нет задач для рассылки | Итерация: #{loop_count}")
            else:
                self.logger.warning(f"[CHECK_RASP_LOOP] Расписание недоступно | Итерация: #{loop_count} | Дата: {self.date} | Причина: rasp_exists=False")
                    


async def main():
    checkrasp = CheckRasp("01_09_2025")
    await checkrasp.send_rasp_test()



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())