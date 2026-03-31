"""
Простой inline-календарь для выбора даты
"""
from datetime import datetime, timedelta
from aiogram import types
from calendar import monthrange


def create_calendar(year: int = None, month: int = None) -> types.InlineKeyboardMarkup:
    """
    Создать inline-календарь для выбора даты
    """
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Названия дней недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    # Создаем клавиатуру
    keyboard = []
    
    # Заголовок с месяцем и годом
    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar:prev_month:{year}:{month}"
        ),
        types.InlineKeyboardButton(
            text=f"{month_names[month-1]} {year}",
            callback_data="calendar:ignore"
        ),
        types.InlineKeyboardButton(
            text="▶️",
            callback_data=f"calendar:next_month:{year}:{month}"
        )
    ])
    
    # Дни недели
    keyboard.append([
        types.InlineKeyboardButton(text=day, callback_data="calendar:ignore")
        for day in weekdays
    ])
    
    # Получаем первый день месяца и количество дней
    first_day_weekday = datetime(year, month, 1).weekday()  # 0 = понедельник
    days_in_month = monthrange(year, month)[1]
    
    # Создаем строки с днями
    week = []
    
    # Пустые ячейки до первого дня месяца
    for _ in range(first_day_weekday):
        week.append(types.InlineKeyboardButton(text=" ", callback_data="calendar:ignore"))
    
    # Дни месяца
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        
        # Пропускаем воскресенья
        if date.weekday() == 6:
            week.append(types.InlineKeyboardButton(
                text=f"🚫{day}",
                callback_data="calendar:ignore"
            ))
        else:
            week.append(types.InlineKeyboardButton(
                text=str(day),
                callback_data=f"calendar:select:{year}:{month}:{day}"
            ))
        
        # Если неделя заполнена, добавляем в клавиатуру
        if len(week) == 7:
            keyboard.append(week)
            week = []
    
    # Добавляем оставшиеся дни
    if week:
        # Дополняем пустыми ячейками
        while len(week) < 7:
            week.append(types.InlineKeyboardButton(text=" ", callback_data="calendar:ignore"))
        keyboard.append(week)
    
    # Кнопка "Сегодня" и "Закрыть"
    keyboard.append([
        types.InlineKeyboardButton(
            text="📅 Сегодня",
            callback_data=f"calendar:today"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def process_calendar_callback(callback_data: str) -> dict:
    """
    Обработать callback от календаря
    Возвращает словарь с действием и данными
    """
    parts = callback_data.split(":")
    
    if len(parts) < 2:
        return {"action": "ignore"}
    
    action = parts[1]
    
    if action == "ignore":
        return {"action": "ignore"}
    
    elif action == "prev_month":
        year, month = int(parts[2]), int(parts[3])
        if month == 1:
            return {"action": "change_month", "year": year - 1, "month": 12}
        else:
            return {"action": "change_month", "year": year, "month": month - 1}
    
    elif action == "next_month":
        year, month = int(parts[2]), int(parts[3])
        if month == 12:
            return {"action": "change_month", "year": year + 1, "month": 1}
        else:
            return {"action": "change_month", "year": year, "month": month + 1}
    
    elif action == "select":
        year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        date = datetime(year, month, day)
        return {
            "action": "select",
            "date": date,
            "date_str": date.strftime("%d_%m_%Y")
        }
    
    elif action == "today":
        today = datetime.now()
        return {
            "action": "select",
            "date": today,
            "date_str": today.strftime("%d_%m_%Y")
        }
    
    return {"action": "ignore"}
