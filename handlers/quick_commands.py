"""
Быстрые команды для расписания
"""
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from utils.rasp import Rasp
from utils.db import DB
from utils.log import create_logger
from utils.decorators import check_chat_type

router = Router()
logger = create_logger(__name__)
db = DB()


@router.message(Command("сегодня", "today"))
@check_chat_type("private")
async def today_schedule(message: types.Message):
    """Расписание на сегодня"""
    logger.info(f"Пользователь {message.from_user.id} запросил расписание на сегодня")
    
    user_data = await db.get(message.from_user.id)
    if not user_data:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    date = datetime.now().strftime("%d_%m_%Y")
    
    # Проверка на воскресенье
    if datetime.now().weekday() == 6:
        await message.answer("📅 Сегодня воскресенье, пар нет!")
        return
    
    rasp = Rasp(date=date)
    await rasp.run_session()
    
    try:
        await rasp.get()
        
        if not rasp.rasp_exists:
            await message.answer("❌ Расписание на сегодня еще не опубликовано")
            return
        
        # Получаем расписание для основной группы
        group_id = user_data[3]

        # Добавляем информацию о пропущенных часах если нужно
        missed_hours = user_data[5]
        show_mode = user_data[6]
               
        # Создаем сообщение с кнопками навигации
        text, kb = await rasp.create_rasp_msg(
            group=int(group_id),
            user_id=message.from_user.id
        )
        if show_mode and "rasp" in show_mode and int(missed_hours) > 0:
            text += f"\n\n⏰ У тебя сейчас <b>{missed_hours}</b> пропущенных часов."

        if not text:
            await message.answer(f"❌ Расписание для группы {group_id} не найдено")
            return   

        await message.answer(text, reply_markup=kb)
        
    finally:
        await rasp.close_session()


@router.message(Command("завтра", "tomorrow"))
@check_chat_type("private")
async def tomorrow_schedule(message: types.Message):
    """Расписание на завтра"""
    logger.info(f"Пользователь {message.from_user.id} запросил расписание на завтра")
    
    user_data = await db.get(message.from_user.id)
    if not user_data:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    # Пропускаем воскресенье
    if tomorrow.weekday() == 6:
        tomorrow = tomorrow + timedelta(days=1)
    
    date = tomorrow.strftime("%d_%m_%Y")
    
    rasp = Rasp(date=date)
    await rasp.run_session()
    
    try:
        await rasp.get()
        
        if not rasp.rasp_exists:
            await message.answer("❌ Расписание на завтра еще не опубликовано")
            return
        
        # Получаем расписание для основной группы
        group_id = user_data[3]
        rasp_text = await rasp.get_rasp(group=str(group_id))
        
        if not rasp_text:
            await message.answer(f"❌ Расписание для группы {group_id} не найдено")
            return
        
        # Добавляем информацию о пропущенных часах если нужно
        missed_hours = user_data[5]
        show_mode = user_data[6]
        
        if show_mode and "rasp" in show_mode and missed_hours > 0:
            rasp_text += f"\n\n⏰ У тебя сейчас <b>{missed_hours}</b> пропущенных часов."
        
        # Создаем сообщение с кнопками навигации
        msg_data = await rasp.create_rasp_msg(
            rasp_text=rasp_text,
            group=str(group_id),
            user_id=message.from_user.id
        )
        
        await message.answer(msg_data["text"], reply_markup=msg_data["keyboard"])
        
    finally:
        await rasp.close_session()


@router.message(Command("неделя", "week"))
@check_chat_type("private")
async def week_schedule(message: types.Message):
    """Расписание на неделю"""
    logger.info(f"Пользователь {message.from_user.id} запросил расписание на неделю")
    
    user_data = await db.get(message.from_user.id)
    if not user_data:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    group_id = user_data[3]
    
    await message.answer("⏳ Загружаю расписание на неделю...")
    
    week_text = f"📅 <b>Расписание на неделю для группы {group_id}</b>\n\n"
    
    current_date = datetime.now()
    days_added = 0
    days_checked = 0
    max_days_to_check = 14  # Проверяем максимум 2 недели
    
    while days_added < 6 and days_checked < max_days_to_check:
        check_date = current_date + timedelta(days=days_checked)
        days_checked += 1
        
        # Пропускаем воскресенье
        if check_date.weekday() == 6:
            continue
        
        date_str = check_date.strftime("%d_%m_%Y")
        
        rasp = Rasp(date=date_str)
        await rasp.run_session()
        
        try:
            await rasp.get()
            
            if rasp.rasp_exists:
                rasp_text = await rasp.get_rasp(group=str(group_id))
                
                if rasp_text:
                    # Форматируем дату
                    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
                    weekday = weekday_names[check_date.weekday()]
                    formatted_date = check_date.strftime("%d.%m.%Y")
                    
                    week_text += f"<b>{weekday}, {formatted_date}</b>\n"
                    week_text += rasp_text + "\n\n"
                    days_added += 1
        finally:
            await rasp.close_session()
    
    if days_added == 0:
        await message.answer("❌ Расписание на неделю еще не опубликовано")
        return
    
    # Добавляем информацию о пропущенных часах
    missed_hours = user_data[5]
    if missed_hours > 0:
        week_text += f"⏰ У тебя сейчас <b>{missed_hours}</b> пропущенных часов."
    
    # Отправляем расписание (может быть длинным, поэтому разбиваем если нужно)
    if len(week_text) > 4096:
        # Telegram ограничивает сообщения 4096 символами
        parts = []
        current_part = ""
        
        for line in week_text.split("\n"):
            if len(current_part) + len(line) + 1 > 4096:
                parts.append(current_part)
                current_part = line + "\n"
            else:
                current_part += line + "\n"
        
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(week_text)
