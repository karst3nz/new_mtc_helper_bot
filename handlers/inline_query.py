"""
Inline-режим для быстрого доступа к расписанию
"""
import os
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from utils.rasp import Rasp
from utils.db import DB
from utils.log import create_logger

router = Router()
logger = create_logger(__name__)
db = DB()


def find_next_schedule_files(start_date: datetime, count: int = 3) -> list[datetime]:
    """
    Найти следующие N дат с существующими файлами расписания
    """
    found_dates = []
    current_date = start_date
    max_days_ahead = 30  # Максимум 30 дней вперед
    
    for _ in range(max_days_ahead):
        # Пропускаем воскресенье
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue
        
        # Проверяем существование файла
        date_str = current_date.strftime("%d_%m_%Y")
        txt_file = f"data/txt/{date_str}.txt"
        
        if os.path.exists(txt_file):
            found_dates.append(current_date)
            if len(found_dates) >= count:
                break
        
        current_date += timedelta(days=1)
    
    return found_dates


@router.inline_query()
async def inline_schedule(query: types.InlineQuery):
    """
    Обработчик inline-запросов
    Примеры:
    - @bot расписание
    - @bot сегодня
    - @bot завтра
    - @bot 01.04
    """
    logger.info(f"Inline-запрос от {query.from_user.id}: '{query.query}'")
    
    user_data = await db.get(query.from_user.id)
    if not user_data:
        # Пользователь не зарегистрирован
        result = InlineQueryResultArticle(
            id="not_registered",
            title="❌ Вы не зарегистрированы",
            description="Сначала запустите бота командой /start",
            input_message_content=InputTextMessageContent(
                message_text="❌ Сначала зарегистрируйтесь через /start"
            )
        )
        await query.answer([result], cache_time=1)
        return
    
    group_id = user_data[3]
    query_text = query.query.lower().strip()
    
    results = []
    
    # Определяем дату на основе запроса
    if not query_text or query_text in ["расписание", "сегодня"]:
        # Показываем 3 ближайших расписания
        available_dates = find_next_schedule_files(datetime.now(), count=3)
        
        if not available_dates:
            results.append(InlineQueryResultArticle(
                id="no_schedules",
                title="❌ Нет доступных расписаний",
                description="Расписания не найдены",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Расписания на ближайшие дни не найдены"
                )
            ))
        else:
            for date in available_dates:
                # Определяем заголовок
                if date.date() == datetime.now().date():
                    title_prefix = "Сегодня"
                elif date.date() == (datetime.now() + timedelta(days=1)).date():
                    title_prefix = "Завтра"
                else:
                    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
                    title_prefix = weekday_names[date.weekday()]
                
                rasp_result = await get_schedule_result(date, group_id, title_prefix)
                if rasp_result:
                    results.append(rasp_result)
    
    elif query_text == "завтра":
        # Расписание на завтра
        date = datetime.now() + timedelta(days=1)
        if date.weekday() == 6:  # Пропускаем воскресенье
            date = date + timedelta(days=1)
        
        rasp_result = await get_schedule_result(date, group_id, "Завтра")
        if rasp_result:
            results.append(rasp_result)
    
    elif query_text == "неделя":
        # Расписание на неделю
        results.append(InlineQueryResultArticle(
            id="week",
            title="📅 Расписание на неделю",
            description=f"Для группы {group_id}",
            input_message_content=InputTextMessageContent(
                message_text=f"📅 Используйте команду /неделя для просмотра расписания на неделю"
            )
        ))
    
    else:
        # Попытка распарсить дату
        try:
            # Формат: 01.04 или 01.04.2026
            parts = query_text.replace(" ", "").split(".")
            if len(parts) == 2:
                day, month = int(parts[0]), int(parts[1])
                year = datetime.now().year
                date = datetime(year, month, day)
            elif len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                date = datetime(year, month, day)
            else:
                raise ValueError("Неверный формат даты")
            
            if date.weekday() == 6:
                results.append(InlineQueryResultArticle(
                    id="sunday_custom",
                    title="📅 Это воскресенье",
                    description="Пар нет!",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📅 {date.strftime('%d.%m.%Y')} - воскресенье, пар нет!"
                    )
                ))
            else:
                rasp_result = await get_schedule_result(
                    date, 
                    group_id, 
                    date.strftime("%d.%m.%Y")
                )
                if rasp_result:
                    results.append(rasp_result)
        
        except (ValueError, IndexError):
            # Неверный формат - показываем подсказки
            results = [
                InlineQueryResultArticle(
                    id="help_today",
                    title="📅 Расписание на сегодня",
                    description="Нажмите для просмотра",
                    input_message_content=InputTextMessageContent(
                        message_text="Используйте: @bot сегодня"
                    )
                ),
                InlineQueryResultArticle(
                    id="help_tomorrow",
                    title="📅 Расписание на завтра",
                    description="Нажмите для просмотра",
                    input_message_content=InputTextMessageContent(
                        message_text="Используйте: @bot завтра"
                    )
                ),
                InlineQueryResultArticle(
                    id="help_date",
                    title="📅 Расписание на конкретную дату",
                    description="Формат: 01.04 или 01.04.2026",
                    input_message_content=InputTextMessageContent(
                        message_text="Используйте: @bot 01.04"
                    )
                )
            ]
    
    if not results:
        results.append(InlineQueryResultArticle(
            id="no_results",
            title="❌ Ничего не найдено",
            description="Попробуйте другой запрос",
            input_message_content=InputTextMessageContent(
                message_text="❌ Расписание не найдено"
            )
        ))
    
    await query.answer(results, cache_time=60)


async def get_schedule_result(date: datetime, group_id: int, title_prefix: str) -> InlineQueryResultArticle | None:
    """
    Получить результат inline-запроса с расписанием
    Работает только с локальными файлами, не делает запросы на сайт
    """
    date_str = date.strftime("%d_%m_%Y")
    
    # Проверяем существование файла
    txt_file = f"data/txt/{date_str}.txt"
    if not os.path.exists(txt_file):
        return None
    
    rasp = Rasp(date=date_str)
    rasp.show_lesson_time = False  # Не показываем время пар в inline
    rasp.rasp_exists = True  # Файл существует
    rasp.rasp_file_exists = True
    
    try:
        # Используем create_rasp_msg для получения полного форматированного расписания
        # но без user_id, чтобы не показывать пропущенные часы
        # _get_new=False означает использовать локальный файл без запроса на сайт
        rasp_text, _ = await rasp.create_rasp_msg(group=group_id, sec_group=None, _get_new=False, user_id=None)
        
        if not rasp_text:
            return InlineQueryResultArticle(
                id=f"no_group_{date_str}",
                title=f"❌ {title_prefix}: группа не найдена",
                description=f"Группа {group_id}",
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ Расписание для группы {group_id} не найдено"
                )
            )
        
        # Получаем первые несколько пар для описания
        lines = rasp_text.split("\n")
        # Пропускаем заголовок и берем первые пары
        description_lines = [line.strip() for line in lines[2:5] if line.strip() and not line.startswith("📅")]
        description = " | ".join(description_lines)
        if len(description) > 100:
            description = description[:97] + "..."
        
        return InlineQueryResultArticle(
            id=f"schedule_{date_str}_{group_id}",
            title=f"📅 {title_prefix} ({date.strftime('%d.%m.%Y')})",
            description=description or f"Расписание для группы {group_id}",
            input_message_content=InputTextMessageContent(
                message_text=rasp_text,
                parse_mode="HTML"
            )
        )
    
    except Exception as e:
        logger.error(f"Ошибка получения расписания для inline: {e}")
        return None
