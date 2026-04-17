import re
from typing import Literal
import config
from utils.decorators import if_admin
from utils.rasp import Rasp
from utils.log import create_logger
from utils.db import DB
from utils.state import States
from utils.export import excel_exporter
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from utils.utils import format_and_return_columns, get_lesson_time
from utils.ui_constants import ButtonFactory, UIConstants
from utils.callback_data import CallbackData
from utils.admin_broadcast import get_broadcast_manager
from utils.admin_user_manager import get_user_manager
from utils.admin_analytics import get_analytics_manager
from utils.admin_monitoring import get_system_monitor, get_quick_actions
from utils.admin_logger import get_admin_logger, get_error_logger
from utils.maintenance_mode import get_maintenance_mode
from utils.admin_notifications import get_admin_notifications
logger = create_logger(__name__)

async def rasp(user_id: int, date: str = None, _get_new: bool = False, show_lessons_time: bool = False):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    if date is None:
        if datetime.today().weekday() != 6:
            date = datetime.today().date().strftime("%d_%m_%Y")
        else:
            date = (datetime.today().date() + timedelta(days=1)).strftime("%d_%m_%Y")
    rasp = Rasp(date, group=group); rasp.show_lesson_time = show_lessons_time
    text, btns = await rasp.create_rasp_msg(
        group=group,
        sec_group=sec_group,
        _get_new=_get_new,
        user_id=user_id
    )
    user = db.get_user_dataclass(user_id)
    if "rasp" in str(user.show_missed_hours_mode): text += f"\n⏰ У тебя сейчас <b>{user.missed_hours}</b> пропущенных часов.\n\n"
    
    # Добавляем кнопку календаря
    calendar_btn = [types.InlineKeyboardButton(text="📅 Выбрать дату", callback_data="menu:show_calendar")]
    if btns.inline_keyboard:
        btns.inline_keyboard.insert(-1, calendar_btn)
    
    return text, btns


async def show_calendar(user_id: int, state: FSMContext):
    """Показать календарь для выбора даты"""
    from utils.calendar_keyboard import create_calendar
    
    await state.clear()
    
    text = "📅 <b>Выберите дату для просмотра расписания</b>\n\n🚫 - воскресенье (выходной)"
    calendar = create_calendar()
    
    return text, calendar



async def start(user_id: int, state: FSMContext): 
    await state.clear()
    db = DB()
    if db.is_exists(user_id) is False:
        text = "👋 Привет! Я бот для просмотра расписания занятий.\n\n📝 Для начала работы, пожалуйста, отправьте номер вашей группы:"
        await state.set_state(States.first_reg_group)
        return text, types.InlineKeyboardMarkup(inline_keyboard=[[]])
    else:
        user = db.get_user_dataclass(user_id)
        if "start" in str(user.show_missed_hours_mode):
            text = (
                f"🎓 Главное меню\n"
                f"⏰ У тебя сейчас <b>{user.missed_hours}</b> пропущенных часов.\n\n"
                "Выберите нужный раздел:"
            )
        else:
            text = (
                "🎓 Главное меню\n\n"
                "Выберите нужный раздел:"
            )
        btns = [
            [types.InlineKeyboardButton(text="📅 Расписание пар", callback_data="menu:rasp")],
            [types.InlineKeyboardButton(text="🔔 Расписание звонков", callback_data=CallbackData.encode("lesson_schedule", "True"))],
            [types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")]
        ]
        if str(user_id) == str(config.ADMIN_ID): btns += [[types.InlineKeyboardButton(text='ADMIN', callback_data="menu:admin")]]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def skip_sec_group(user_id: int, state: FSMContext):
    state_data = await state.get_data()
    group = state_data.get("group")
    await state.clear()
    db = DB()
    db.insert(
        user_id=user_id,
        tg_username=None,
        group_id=group,
        sec_group_id=None
    )
    text, btns = await start(user_id=user_id, state=state)
    return text, btns


async def settings(user_id: int, state: FSMContext):
    db = DB()
    userDC = db.get_user_dataclass(user_id)
    group, sec_group = userDC.group_id, userDC.sec_group_id
    await state.clear()
    smena_str = f"{userDC.smena}-ая" if userDC.smena else "<i>не указана</i>"
    missed_hours_modes = {
        "start": "В главном меню",
        "rasp": "В просмотре расписания",
        "newRasp": "В новом/измененном расписании"
    }
    def get_checkbox(mode):
        return '✅' if userDC.show_missed_hours_mode and mode in userDC.show_missed_hours_mode else '❌'

    missed_hours_text = "\n".join(
        [f"  • {desc} {get_checkbox(mode)}" for mode, desc in missed_hours_modes.items()]
    )

    text = (
        "⚙️ <b>Настройки профиля</b>\n\n"
        f"📋 <b>Основная группа:</b> <b>{group}</b>\n"
        f"📋 <b>Дополнительная группа:</b> <b>{sec_group if sec_group is not None else '<i>не указана</i>'}</b>\n"
        f"🔄 <b>Текущая смена:</b> <b>{smena_str}</b>\n"
        f"⏰ <b>Отображение пропущенных часов:</b>\n"
        f"{missed_hours_text}"
    )
 
    btns = [
        [types.InlineKeyboardButton(text="✏️ Изменить основную группу", callback_data="menu:change_main_group")],
        [types.InlineKeyboardButton(text="✏️ Изменить доп. группу" if sec_group is not None else "➕ Добавить доп. группу", callback_data="menu:change_sec_group")],
        [types.InlineKeyboardButton(text="🔄 Изменить смену", callback_data="menu:smena_edit")],
        [types.InlineKeyboardButton(text="⏰ Отображение пропущенных часов", callback_data="menu:missed_hours_mode")],
        [types.InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu:notification_settings")],
        # [types.InlineKeyboardButton(text="📥 Экспорт всех данных (PDF)", callback_data="menu:export_all_data")],
        [ButtonFactory.back("menu:start")]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_main_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    await state.clear()
    text = f"✏️ Изменение основной группы\n\n📋 Текущая группа: <b>{group}</b>\n\n📝 Отправьте новый номер группы:"
    btns = [
        [ButtonFactory.cancel("menu:settings")]
    ]
    await state.set_state(States.change_main_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)

async def change_sec_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    await state.clear()
    if sec_group is not None:
        text = f"✏️ Изменение дополнительной группы\n\n📋 Текущая доп. группа: <b>{sec_group}</b>\n\n📝 Отправьте новый номер группы:"
    else:
        text = "➕ Добавление дополнительной группы\n\n📝 Отправьте номер дополнительной группы:\n\n💡 <i>Дополнительная группа будет отображаться в расписании вместе с основной</i>"
    btns = [
        [types.InlineKeyboardButton(text="🗑️ Удалить доп. группу", callback_data="menu:delete_sec_group")],
        [ButtonFactory.cancel("menu:settings")]
    ]
    await state.set_state(States.change_sec_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def delete_sec_group(user_id: int, state: FSMContext):
    """Показать подтверждение удаления дополнительной группы"""
    db = DB()
    await state.clear()
    user = db.get_user_dataclass(user_id)
    
    if user.sec_group_id is None:
        text = "ℹ️ У вас нет дополнительной группы"
        btns = [
            [ButtonFactory.back("menu:settings")]
        ]
    else:
        text = (
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить дополнительную группу?\n\n"
            f"📋 Группа: <b>{user.sec_group_id}</b>\n\n"
            f"⚠️ <i>После удаления расписание этой группы не будет отображаться</i>"
        )
        btns = [
            [
                types.InlineKeyboardButton(text="✅ Да, удалить", callback_data="menu:delete_sec_group_execute"),
                ButtonFactory.cancel("menu:settings")
            ]
        ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def delete_sec_group_execute(user_id: int, state: FSMContext):
    """Выполнить удаление дополнительной группы после подтверждения"""
    db = DB()
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="◀️ Вернуться", callback_data="menu:settings")]
    ]
    if db.update(user_id=user_id, column="sec_group_id", new_data=None, table="users") is True:
        text = "✅ Дополнительная группа успешно удалена!"
    else:
        text = "❌ Произошла ошибка при удалении дополнительной группы"
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)

@if_admin("user_id")
async def admin(user_id: int, state: FSMContext):
    await state.clear()
    
    # Получаем краткую статистику
    db = DB()
    total_users = len(db.get_all("user_id", db.users_table))
    
    text = "🛠️ <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
    text += f"👥 Пользователей: <b>{total_users}</b>\n\n"
    text += "Выберите раздел:"
    
    btns = [
        [
            types.InlineKeyboardButton(text="📢 Рассылка", callback_data="menu:broadcast_main"),
            types.InlineKeyboardButton(text="👥 Пользователи", callback_data="menu:users_management")
        ],
        [
            types.InlineKeyboardButton(text="📊 Аналитика", callback_data="menu:analytics_main"),
            types.InlineKeyboardButton(text="📝 Мониторинг", callback_data="menu:monitoring_main")
        ],
        [
            types.InlineKeyboardButton(text="🗄️ База данных", callback_data="menu:database"),
            types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:bot_settings")
        ],
        [types.InlineKeyboardButton(text="⚡ Быстрые действия", callback_data="menu:quick_actions")],
        [ButtonFactory.back("menu:start")]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)

@if_admin("user_id")
async def database(user_id: int, state: FSMContext):
    db = DB()
    await state.clear()
    db_all_users = (
        'Краткая сводка по БД:\n'
        f'Количество пользователей: {len(db.get_all("id", db.users_table))}\n\n'
        # f'Количество бесед: {len(db.get_all("tg_group_id", db.users_table))}\n'
        # f'Общее количество участников в беседах: '
        # f'{sum(int(db.get_all("count_members", db.users_table)))}\n'
    )
    border = "*________________________________________*"
    group_info_start = 'Информация по группам:'

    # Получаем все значения group_id из таблицы users
    all_group_ids = db.get_all("group_id", db.users_table)
    # Оставляем только не пустые и не None значения
    all_group_ids = [g for g in all_group_ids if g not in (None, '', 'None')]

    # Считаем количество пользователей в каждой группе
    from collections import Counter
    group_counter = Counter(all_group_ids)

    # Сортируем группы по количеству пользователей по убыванию
    final_list_group = [
        f"{group} - {count}" for group, count in group_counter.most_common()
    ]

    group_text = ''
    for x in final_list_group:
        group_text += x + "\n"

    y = format_and_return_columns(group_text)
    final_text = f"{db_all_users}{border}\n{group_info_start}\n{y}"

    db_info_buttons = [
        [types.InlineKeyboardButton(text="📤 Выгрузить информацию по человеку", callback_data="menu:db_user")],
        [types.InlineKeyboardButton(text="📤 Выгрузить информацию по группе", callback_data="menu:db_group")],
        [ButtonFactory.back("menu:admin")]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=db_info_buttons)
    return final_text, reply_markup

@if_admin("user_id")
async def db_user(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.db_user_info)
    return '🔎 user_id?', types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:database")]])

@if_admin("user_id")
async def db_group(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.db_group_info)
    return '🔎 group?', types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.back("menu:database")]])


@if_admin("user_id")
async def ad(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.ad_msg)
    return "✉️ Отправь текст", types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.cancel("menu:admin")]])


async def add_missing_hours(user_id: int, state: FSMContext):
    await state.clear()
    db = DB()
    user = db.get_user_dataclass(user_id)
    text = (
        f"⏰ У тебя сейчас пропущенно {user.missed_hours}ч.\n\n"
        "✍️ Отправь, сколько часов ты уже пропустил. Я их прибавлю к текущим"
    )
    btns = [
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="menu:hours_analytics")],
        [types.InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="menu:export_hours")],
        [types.InlineKeyboardButton(text="🗑️ Очистить", callback_data="menu:clear_missing_hours")],
        [ButtonFactory.cancel("delete_msg")]
    ]
    await state.set_state(States.add_missing_hours)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def clear_missing_hours(user_id: int, state: FSMContext):
    """Показать подтверждение очистки часов"""
    await state.clear()
    db = DB()
    user = db.get_user_dataclass(user_id)
    
    text = (
        f"⚠️ <b>Подтверждение очистки</b>\n\n"
        f"Вы уверены, что хотите очистить пропущенные часы?\n\n"
        f"📊 Будет удалено: <b>{user.missed_hours}</b> часов\n\n"
        f"⚠️ <i>Это действие нельзя отменить!</i>"
    )
    
    btns = [
        [
            types.InlineKeyboardButton(text="✅ Да, очистить", callback_data="menu:clear_missing_hours_execute"),
            ButtonFactory.cancel("menu:add_missing_hours")
        ]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def clear_missing_hours_execute(user_id: int, state: FSMContext):
    """Выполнить очистку часов после подтверждения"""
    await state.clear()
    db = DB()
    user = db.get_user_dataclass(user_id)
    prev = int(user.missed_hours) if user.missed_hours else 0
    
    try:
        # Обнуляем счетчик
        db.cursor.execute("UPDATE users SET missed_hours = 0 WHERE user_id = ?", (user_id,))
        db.conn.commit()
        
        # Записываем в историю отрицательное значение (отработка часов)
        if prev > 0:
            db.add_hours_history(user_id, -prev)
        
        text = (
            f"✅ <b>Пропущенные часы успешно очищены!</b>\n\n"
            f"📊 Значение до очистки: <b>{prev}</b> часов\n"
            f"📊 Текущее значение: <b>0</b> часов"
        )
    except Exception as e:
        text = f"❌ Произошла ошибка при очистке пропущенных часов: {e}"
    
    btns = [
        [types.InlineKeyboardButton(text="◀️ Вернуться к пропущенным часам", callback_data="menu:add_missing_hours")],
        [ButtonFactory.close()]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def missed_hours_mode(user_id: int, mode: str = None):
    db = DB()
    if mode is not None and isinstance(mode, FSMContext) is False:
        db.update_hours_mode(user_id, mode)
    user = db.get_user_dataclass(user_id)
    show_missed_hours_mode = user.show_missed_hours_mode
    btns = [
        [types.InlineKeyboardButton(
            text="Главное меню" + (" ❌" if show_missed_hours_mode is None or 'start' not in show_missed_hours_mode else " ✅️"),
            callback_data=CallbackData.encode("missed_hours_mode", "start")
        )],
        [types.InlineKeyboardButton(
            text="Просмотр расписания" + (" ❌" if show_missed_hours_mode is None or 'rasp' not in show_missed_hours_mode else " ✅️"),
            callback_data=CallbackData.encode("missed_hours_mode", "rasp")
        )],
        [types.InlineKeyboardButton(
            text="Новое расписание" + (" ❌" if show_missed_hours_mode is None or 'newRasp' not in show_missed_hours_mode else " ✅️"),
            callback_data=CallbackData.encode("missed_hours_mode", "newRasp")
        )],
        [types.InlineKeyboardButton(
            text="Назад",
            callback_data="menu:settings"
        )]
    ]
    return "⏰ Показ пропущенных часов", types.InlineKeyboardMarkup(inline_keyboard=btns)


async def group_settings(id: int, mode: str = None):
    db = DB()
    if mode is not None and mode == "pin_new_rasp":
        condition = bool(db.get_TGgroup_dataclass(id).pin_new_rasp)
        db.cursor.execute("UPDATE groups SET pin_new_rasp = ? WHERE id = ?", (not bool(condition), id))
        db.conn.commit()
        del condition
    condition = bool(db.get_TGgroup_dataclass(id).pin_new_rasp)
    btns = [
        [types.InlineKeyboardButton(text=f"{'❌' if condition is False else '✅️'} Закреплять новое расписание", callback_data=CallbackData.encode("group_settings", "pin_new_rasp"))],
        [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data="menu:change_GROUP_group")], # по другому не придумал xD
        [ButtonFactory.close()]
    ]
    return "⚙️ Настройки", types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_GROUP_group(id: int, state: FSMContext):
    db = DB()
    try:
        group = db.cursor.execute('SELECT "group" FROM groups WHERE id = ?', (id,)).fetchone()[0]
    except Exception:
        return "❌ Не удалось найти вашу группу в базе, попробуйте передобавить бота", types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.close()]])
    text = f"""
✏️ Изменение группы

📋 Текущая группа: {group}

📝 Отправьте новый номер группы:
        """
    await state.set_state(States.GROUP_change_group)
    await state.update_data(id=id)
    return text, types.InlineKeyboardMarkup(inline_keyboard=[[ButtonFactory.close()]]) 



async def quantity_lessons(user_id: int, date: str, show_lesson_time: bool = False):
    db = DB()
    group = db.get_user_dataclass(user_id).group_id
    rasp = Rasp(group=group)
    lessons_dict = rasp.count_quantity_lessons(group)
    if lessons_dict:
        lessons_text = ""
        total = 0
        for idx, (lesson, count) in enumerate(lessons_dict.items(), start=1):
            lessons_text += f"{idx}. <b>{lesson}</b> — <code>{count}</code> {'пара' if count == 1 else 'пары' if count in [2,3,4] else 'пар'}\n"
            total += count
        text = (
            f"📊 <b>Статистика по предметам для группы <u>{group}</u></b>\n\n"
            f"{lessons_text}\n"
            f"<b>Всего пройдено пар:</b> <code>{total}</code>\n\n"
            f"<i>Пары, которые разделяются на 2 подгруппы, теперь считаются как 1 пара!</i>\n"
            f"<i><b>Данные могут быть неверными!</b></i>"
        )
    else:
        text = (
            f"ℹ️ Для группы <b>{group}</b> нет данных о проведённых парах.\n"
            f"Возможно, вы выбрали неправильную группу или расписаний пока нет."
        )

    btns = [[ButtonFactory.back(f"menu:rasp?{(date, False, show_lesson_time)}")]]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def smena_edit(user_id: int, smena: str = None):
    from utils.utils import get_lessons_timeDT
    db = DB()
    if smena == "1":
        db.update(user_id, "smena", "1", db.users_table)
    elif smena == "2":
        db.update(user_id, "smena", "2", db.users_table)
    userDC = db.get_user_dataclass(user_id)
    def get_btn_text(_smena: str):
        return f"✅️ {_smena} смена" if userDC.smena == _smena else f"{_smena} смена"
    btns = [
        [types.InlineKeyboardButton(text=get_btn_text("1"), callback_data=CallbackData.encode("smena_edit", "1"))],
        [types.InlineKeyboardButton(text=get_btn_text("2"), callback_data=CallbackData.encode("smena_edit", "2"))],
        [ButtonFactory.back("menu:settings")]
    ]
    lessons = get_lessons_timeDT().weekday.shifts.get(userDC.smena)
    lessons_text = ""
    for lesson_num, lesson_name in lessons.items():
        if "/" not in lesson_num:
            lesson_num_fmt = f"{lesson_num}"
            line = f"<b>{lesson_num_fmt}</b>: <i>{lesson_name}</i>\n"
        else:
            line = f"   <i>{lesson_name}</i>\n"
        lessons_text += line

    text = (
        f"<b>🔄 Текущая смена:</b> <b>{userDC.smena}-ая</b>\n\n"
        f"<b>🕰️ Расписание звонков для вашей смены:</b>\n"
        f"<code>{lessons_text}</code>\n"
        f"<i>Выберите нужную смену кнопками ниже.</i>"
    )
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def lesson_schedule(chat_id: int, weekday: Literal["True", "False"] = "True"):
    from utils.utils import get_lessons_timeDT
    db = DB()
    userDC = db.get_user_dataclass(chat_id)
    lessons = get_lessons_timeDT().weekday.shifts.get(userDC.smena) if weekday == "True" else get_lessons_timeDT().weekend.shifts.get(userDC.smena)
    lessons_text = ""
    for lesson_num, lesson_name in lessons.items():
        if "/" not in lesson_num:
            lesson_num_fmt = f"{lesson_num}"
            line = f"<b>{lesson_num_fmt}</b>: <i>{lesson_name}</i>\n"
        else:
            line = f"   <i>{lesson_name}</i>\n"
        lessons_text += line
    text = (
        f"<b>🕰️ Расписание звонков:</b>\n\n"
        f"<code>{lessons_text}</code>"
    )    

    btns = [
        [types.InlineKeyboardButton(text=f"✅️ Пн-Пт" if weekday == "True" else f"Пн-Пт", callback_data=CallbackData.encode("lesson_schedule", "True"))],
        [types.InlineKeyboardButton(text=f"✅️ Суббота" if weekday == "False" else f"Суббота", callback_data=CallbackData.encode("lesson_schedule", "False"))],
        [ButtonFactory.close()]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# ========== МЕНЮ НАСТРОЕК УВЕДОМЛЕНИЙ ==========

async def notification_settings(user_id: int, state: FSMContext):
    """Меню настроек уведомлений"""
    db = DB()
    await state.clear()
    
    # Получаем или создаем настройки уведомлений
    settings = db.get_notification_settings(user_id)
    if not settings:
        db.create_notification_settings(user_id)
        settings = db.get_notification_settings(user_id)
    
    def get_status(enabled):
        return "✅ Включено" if enabled else "❌ Выключено"
    
    text = (
        "🔔 <b>Настройки уведомлений</b>\n\n"
        f"📅 <b>Ежедневное расписание:</b> {get_status(settings['daily_schedule'])}\n"
        f"   Время отправки: <b>{settings['daily_schedule_time']}</b>\n\n"
        f"⏰ <b>Напоминания о парах:</b> {get_status(settings['lesson_reminder'])}\n"
        f"   За <b>{settings['lesson_reminder_minutes']}</b> минут до начала\n\n"
        f"⚠️ <b>Уведомления о пропусках:</b> {get_status(settings['hours_notification'])}\n"
        f"   Порог: <b>{settings['hours_threshold']}</b> часов\n\n"
        "💡 <i>Настройте уведомления под себя</i>"
    )
    
    btns = [
        [types.InlineKeyboardButton(
            text=f"📅 Ежедневное расписание: {'✅' if settings['daily_schedule'] else '❌'}", 
            callback_data="menu:toggle_daily_schedule"
        )],
        [types.InlineKeyboardButton(
            text="🕐 Изменить время отправки", 
            callback_data="menu:change_daily_time"
        )],
        [types.InlineKeyboardButton(
            text=f"⏰ Напоминания о парах: {'✅' if settings['lesson_reminder'] else '❌'}", 
            callback_data="menu:toggle_lesson_reminder"
        )],
        [types.InlineKeyboardButton(
            text="⏱️ Изменить время напоминания", 
            callback_data="menu:change_reminder_time"
        )],
        [types.InlineKeyboardButton(
            text=f"⚠️ Уведомления о пропусках: {'✅' if settings['hours_notification'] else '❌'}", 
            callback_data="menu:toggle_hours_notification"
        )],
        [types.InlineKeyboardButton(
            text="📊 Изменить порог пропусков", 
            callback_data="menu:change_hours_threshold"
        )],
        [ButtonFactory.back("menu:settings")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def toggle_daily_schedule(user_id: int, state: FSMContext):
    """Переключить ежедневное расписание"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    new_value = not settings['daily_schedule']
    db.update_notification_setting(user_id, 'daily_schedule', int(new_value))
    
    return await notification_settings(user_id, state)


async def toggle_lesson_reminder(user_id: int, state: FSMContext):
    """Переключить напоминания о парах"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    new_value = not settings['lesson_reminder']
    db.update_notification_setting(user_id, 'lesson_reminder', int(new_value))
    
    return await notification_settings(user_id, state)


async def toggle_hours_notification(user_id: int, state: FSMContext):
    """Переключить уведомления о пропусках"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    new_value = not settings['hours_notification']
    db.update_notification_setting(user_id, 'hours_notification', int(new_value))
    
    return await notification_settings(user_id, state)


async def change_daily_time(user_id: int, state: FSMContext):
    """Изменить время отправки ежедневного расписания"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    
    text = (
        "🕐 <b>Изменение времени отправки</b>\n\n"
        f"Текущее время: <b>{settings['daily_schedule_time']}</b>\n\n"
        "Выберите новое время:"
    )
    
    times = ["18:00", "19:00", "20:00", "21:00", "22:00"]
    btns = []
    
    for time in times:
        emoji = "✅" if time == settings['daily_schedule_time'] else "🕐"
        btns.append([types.InlineKeyboardButton(
            text=f"{emoji} {time}", 
            callback_data=CallbackData.encode("set_daily_time", time)
        )])
    
    btns.append([ButtonFactory.back("menu:notification_settings")])
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def set_daily_time(user_id: int, time: str, state: FSMContext = None):
    """Установить время отправки ежедневного расписания"""
    db = DB()
    db.update_notification_setting(user_id, 'daily_schedule_time', time)
    
    if state is None:
        from config import FSMContext
        state = FSMContext()
    return await notification_settings(user_id, state)


async def change_reminder_time(user_id: int, state: FSMContext):
    """Изменить время напоминания о парах"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    
    text = (
        "⏱️ <b>Изменение времени напоминания</b>\n\n"
        f"Текущее: за <b>{settings['lesson_reminder_minutes']}</b> минут\n\n"
        "Выберите за сколько минут до начала пар напоминать:"
    )
    
    minutes = [15, 30, 45, 60]
    btns = []
    
    for mins in minutes:
        emoji = "✅" if mins == settings['lesson_reminder_minutes'] else "⏱️"
        btns.append([types.InlineKeyboardButton(
            text=f"{emoji} За {mins} минут", 
            callback_data=CallbackData.encode("set_reminder_time", mins)
        )])
    
    btns.append([ButtonFactory.back("menu:notification_settings")])
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def set_reminder_time(user_id: int, minutes: int, state: FSMContext = None):
    """Установить время напоминания о парах"""
    db = DB()
    db.update_notification_setting(user_id, 'lesson_reminder_minutes', minutes)
    
    if state is None:
        from config import FSMContext
        state = FSMContext()
    return await notification_settings(user_id, state)


async def change_hours_threshold(user_id: int, state: FSMContext):
    """Изменить порог пропущенных часов"""
    db = DB()
    settings = db.get_notification_settings(user_id)
    
    text = (
        "📊 <b>Изменение порога пропусков</b>\n\n"
        f"Текущий порог: <b>{settings['hours_threshold']}</b> часов\n\n"
        "Выберите новый порог (при достижении придет уведомление):"
    )
    
    thresholds = [10, 20, 30, 40, 50]
    btns = []
    
    for threshold in thresholds:
        emoji = "✅" if threshold == settings['hours_threshold'] else "📊"
        btns.append([types.InlineKeyboardButton(
            text=f"{emoji} {threshold} часов", 
            callback_data=CallbackData.encode("set_hours_threshold", threshold)
        )])
    
    btns.append([ButtonFactory.back("menu:notification_settings")])
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def set_hours_threshold(user_id: int, threshold: int, state: FSMContext = None):
    """Установить порог пропущенных часов"""
    db = DB()
    db.update_notification_setting(user_id, 'hours_threshold', threshold)
    
    if state is None:
        from config import FSMContext
        state = FSMContext()
    return await notification_settings(user_id, state)


# ========== АНАЛИТИКА И ЭКСПОРТ ==========

async def hours_analytics(user_id: int, state: FSMContext):
    """Показать аналитику пропущенных часов"""
    from utils.analytics import analytics
    from config import bot
    
    await state.clear()
    
    db = DB()
    
    # Получаем статистику
    stats = analytics.get_attendance_stats(user_id, 30)
    comparison = analytics.get_comparison_with_previous_period(user_id, 30)
    
    # Формируем текст
    text = (
        "📊 <b>Статистика пропущенных часов</b>\n\n"
        f"📅 <b>За последние 30 дней:</b>\n"
        f"  • Всего пропущено: <b>{stats['total_hours']}</b> часов\n"
        f"  • Среднее в день: <b>{stats['avg_per_day']:.1f}</b> часов\n"
        f"  • Максимум за день: <b>{stats['max_day']}</b> часов\n"
        f"  • Дней с пропусками: <b>{stats['days_with_misses']}</b> из {stats['total_days']}\n\n"
        f"📈 <b>Сравнение с предыдущим периодом:</b>\n"
        f"  • Текущий период: <b>{comparison['current_period']}</b> ч\n"
        f"  • Предыдущий период: <b>{comparison['previous_period']}</b> ч\n"
        f"  • Изменение: <b>{comparison['change']:+d}</b> ч ({comparison['change_percent']:+.1f}%)\n"
    )
    
    if comparison['is_improvement']:
        text += "\n✅ <b>Отлично! Пропусков стало меньше!</b>"
    elif comparison['change'] > 0:
        text += "\n⚠️ <b>Пропусков стало больше. Будьте внимательнее!</b>"
    else:
        text += "\n📊 <b>Без изменений</b>"
    
    btns = [
        [types.InlineKeyboardButton(text="📈 График за 30 дней", callback_data=CallbackData.encode("show_chart", 30))],
        [types.InlineKeyboardButton(text="📊 Недельное сравнение", callback_data="menu:show_weekly_chart")],
        [ButtonFactory.back("menu:add_missing_hours")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def show_chart(user_id: int, days: int, state: FSMContext = None):
    """Показать график посещаемости"""
    from utils.analytics import analytics
    from config import bot
    from aiogram.types import BufferedInputFile
    
    if state:
        await state.clear()
    
    # Генерируем график
    chart_bytes = await analytics.generate_attendance_chart(user_id, days)
    
    # Отправляем как фото
    photo = BufferedInputFile(chart_bytes, filename=f"chart_{user_id}.png")
    
    # Возвращаем специальный маркер для отправки фото
    return {"type": "photo", "photo": photo, "caption": f"📈 График пропущенных часов за последние {days} дней"}


async def show_weekly_chart(user_id: int, state: FSMContext):
    """Показать недельное сравнение"""
    from utils.analytics import analytics
    from config import bot
    from aiogram.types import BufferedInputFile
    
    await state.clear()
    
    # Генерируем график
    chart_bytes = await analytics.generate_weekly_comparison(user_id)
    
    # Отправляем как фото
    photo = BufferedInputFile(chart_bytes, filename=f"weekly_chart_{user_id}.png")
    
    return {"type": "photo", "photo": photo, "caption": "📊 Сравнение пропусков по неделям"}


async def export_hours(user_id: int, state: FSMContext):
    """Экспорт истории пропущенных часов в Excel"""
    from utils.export import excel_exporter
    from config import bot
    from aiogram.types import FSInputFile
    
    await state.clear()
    
    try:
        # Генерируем Excel файл
        filepath = await excel_exporter.export_hours_history(user_id, 30)
        
        # Возвращаем специальный маркер для отправки документа
        return {
            "type": "document",
            "document": FSInputFile(filepath),
            "caption": "📥 История пропущенных часов за последние 30 дней"
        }
    
    except Exception as e:
        text = f"❌ Ошибка при экспорте данных: {e}"
        btns = [[ButtonFactory.back("menu:add_missing_hours")]]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def download_schedules(user_id: int, state: FSMContext):
    """Выгрузка всех файлов расписания с сайта"""
    await state.clear()
    
    text = (
        "📥 <b>Выгрузка расписаний с сайта</b>\n\n"
        "Выберите тип расписания для выгрузки:"
    )
    
    btns = [
        [types.InlineKeyboardButton(text="📅 Расписание студентов", callback_data="menu:download_student_schedules")],
        [types.InlineKeyboardButton(text="👨‍🏫 Расписание преподавателей", callback_data="menu:download_teacher_schedules")],
        [types.InlineKeyboardButton(text="📦 Все расписания", callback_data="menu:download_all_schedules")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def download_student_schedules(user_id: int, state: FSMContext):
    """Выгрузка расписаний студентов в data/txt за весь год назад"""
    from datetime import datetime, timedelta
    import os
    
    await state.clear()
    
    text = "⏳ Начинаю выгрузку расписаний студентов за год...\n\n"
    
    try:
        # Получаем даты за весь год назад (365 дней)
        dates_to_download = []
        current_date = datetime.now()
        
        for i in range(365):
            date = current_date - timedelta(days=i)
            date_str = date.strftime("%d_%m_%Y")
            dates_to_download.append((date_str, date.strftime("%d.%m.%Y")))
        
        # Загружаем файлы
        downloaded = 0
        failed = 0
        skipped_not_published = 0
        skipped_exists = 0
        
        for date_str, display_date in dates_to_download:
            # Проверяем, существует ли уже файл
            txt_path = f"data/txt/{date_str}.txt"
            if os.path.exists(txt_path):
                skipped_exists += 1
                continue
            
            rasp = Rasp(date=date_str, is_teacher=False)
            
            try:
                await rasp.run_session()
                await rasp.get()
                
                if rasp.rasp_exists:
                    downloaded += 1
                    if downloaded % 10 == 0:  # Показываем прогресс каждые 10 файлов
                        text += f"✅ Загружено {downloaded} файлов...\n"
                else:
                    skipped_not_published += 1
                    
                await rasp.close_session()
                
            except Exception as e:
                failed += 1
                try:
                    await rasp.close_session()
                except:
                    pass
        
        text += f"\n📊 <b>Итого:</b>\n"
        text += f"✅ Загружено: {downloaded}\n"
        text += f"📁 Уже существует: {skipped_exists}\n"
        text += f"⏭️ Не опубликовано: {skipped_not_published}\n"
        text += f"❌ Ошибок: {failed}\n"
        text += f"📁 Сохранено в: data/txt/"
        
    except Exception as e:
        text = f"❌ Ошибка при выгрузке: {e}"
    
    btns = [
        [ButtonFactory.back("menu:download_schedules")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def download_teacher_schedules(user_id: int, state: FSMContext):
    """Выгрузка расписаний преподавателей в data/teach_txt за весь год назад"""
    from datetime import datetime, timedelta
    import os
    
    await state.clear()
    
    text = "⏳ Начинаю выгрузку расписаний преподавателей за год...\n\n"
    
    try:
        # Получаем даты за весь год назад (365 дней)
        dates_to_download = []
        current_date = datetime.now()
        
        for i in range(365):
            date = current_date - timedelta(days=i)
            date_str = date.strftime("%d_%m_%Y")
            dates_to_download.append((date_str, date.strftime("%d.%m.%Y")))
        
        # Загружаем файлы
        downloaded = 0
        failed = 0
        skipped_not_published = 0
        skipped_exists = 0
        
        for date_str, display_date in dates_to_download:
            # Проверяем, существует ли уже файл
            txt_path = f"data/teach_txt/{date_str}.txt"
            if os.path.exists(txt_path):
                skipped_exists += 1
                continue
            
            rasp = Rasp(date=date_str, is_teacher=True)
            
            try:
                await rasp.run_session()
                await rasp.get()
                
                if rasp.rasp_exists:
                    downloaded += 1
                    if downloaded % 10 == 0:  # Показываем прогресс каждые 10 файлов
                        text += f"✅ Загружено {downloaded} файлов...\n"
                else:
                    skipped_not_published += 1
                    
                await rasp.close_session()
                
            except Exception as e:
                failed += 1
                try:
                    await rasp.close_session()
                except:
                    pass
        
        text += f"\n📊 <b>Итого:</b>\n"
        text += f"✅ Загружено: {downloaded}\n"
        text += f"📁 Уже существует: {skipped_exists}\n"
        text += f"⏭️ Не опубликовано: {skipped_not_published}\n"
        text += f"❌ Ошибок: {failed}\n"
        text += f"📁 Сохранено в: data/teach_txt/"
        
    except Exception as e:
        text = f"❌ Ошибка при выгрузке: {e}"
    
    btns = [
        [ButtonFactory.back("menu:download_schedules")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def download_all_schedules(user_id: int, state: FSMContext):
    """Выгрузка всех расписаний (студенты + преподаватели) за весь год назад"""
    from datetime import datetime, timedelta
    import os
    
    await state.clear()
    
    text = "⏳ Начинаю выгрузку всех расписаний за год...\n\n"
    
    try:
        # Получаем даты за весь год назад (365 дней)
        dates_to_download = []
        current_date = datetime.now()
        
        for i in range(365):
            date = current_date - timedelta(days=i)
            date_str = date.strftime("%d_%m_%Y")
            dates_to_download.append((date_str, date.strftime("%d.%m.%Y")))
        
        # Загружаем файлы студентов
        downloaded_students = 0
        skipped_students_exists = 0
        skipped_students_not_published = 0
        failed_students = 0
        
        text += "📅 <b>Расписания студентов:</b>\n"
        
        for date_str, display_date in dates_to_download:
            # Проверяем, существует ли уже файл
            txt_path = f"data/txt/{date_str}.txt"
            if os.path.exists(txt_path):
                skipped_students_exists += 1
                continue
            
            rasp = Rasp(date=date_str, is_teacher=False)
            
            try:
                await rasp.run_session()
                await rasp.get()
                
                if rasp.rasp_exists:
                    downloaded_students += 1
                    if downloaded_students % 10 == 0:
                        text += f"✅ Загружено {downloaded_students} файлов...\n"
                else:
                    skipped_students_not_published += 1
                    
                await rasp.close_session()
                
            except Exception:
                failed_students += 1
                try:
                    await rasp.close_session()
                except:
                    pass
        
        text += f"✅ Загружено: {downloaded_students}\n"
        text += f"📁 Уже существует: {skipped_students_exists}\n"
        text += f"⏭️ Не опубликовано: {skipped_students_not_published}\n"
        text += f"❌ Ошибок: {failed_students}\n\n"
        
        # Загружаем файлы преподавателей
        downloaded_teachers = 0
        skipped_teachers_exists = 0
        skipped_teachers_not_published = 0
        failed_teachers = 0
        
        text += "👨‍🏫 <b>Расписания преподавателей:</b>\n"
        
        for date_str, display_date in dates_to_download:
            # Проверяем, существует ли уже файл
            txt_path = f"data/teach_txt/{date_str}.txt"
            if os.path.exists(txt_path):
                skipped_teachers_exists += 1
                continue
            
            rasp = Rasp(date=date_str, is_teacher=True)
            
            try:
                await rasp.run_session()
                await rasp.get()
                
                if rasp.rasp_exists:
                    downloaded_teachers += 1
                    if downloaded_teachers % 10 == 0:
                        text += f"✅ Загружено {downloaded_teachers} файлов...\n"
                else:
                    skipped_teachers_not_published += 1
                    
                await rasp.close_session()
                
            except Exception:
                failed_teachers += 1
                try:
                    await rasp.close_session()
                except:
                    pass
        
        text += f"✅ Загружено: {downloaded_teachers}\n"
        text += f"📁 Уже существует: {skipped_teachers_exists}\n"
        text += f"⏭️ Не опубликовано: {skipped_teachers_not_published}\n"
        text += f"❌ Ошибок: {failed_teachers}\n\n"
        
        text += f"📊 <b>Итого:</b>\n"
        text += f"✅ Всего загружено: {downloaded_students + downloaded_teachers}\n"
        text += f"📁 Всего существует: {skipped_students_exists + skipped_teachers_exists}\n"
        text += f"⏭️ Всего не опубликовано: {skipped_students_not_published + skipped_teachers_not_published}\n"
        text += f"❌ Всего ошибок: {failed_students + failed_teachers}\n"
        text += f"📁 Студенты: data/txt/\n"
        text += f"📁 Преподаватели: data/teach_txt/"
        
    except Exception as e:
        text = f"❌ Ошибка при выгрузке: {e}"
    
    btns = [
        [ButtonFactory.back("menu:download_schedules")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def test_notifications(user_id: int, state: FSMContext):
    """Меню тестирования уведомлений"""
    await state.clear()
    
    text = (
        "🔔 <b>Тестирование уведомлений</b>\n\n"
        "Выберите тип уведомления для тестирования:"
    )
    
    btns = [
        [types.InlineKeyboardButton(text="📅 Ежедневное расписание", callback_data="menu:test_daily_schedule")],
        [types.InlineKeyboardButton(text="⏰ Напоминание о парах", callback_data="menu:test_lesson_reminder")],
        [types.InlineKeyboardButton(text="⚠️ Уведомление о пропусках", callback_data="menu:test_hours_notification")],
        [types.InlineKeyboardButton(text="📊 Статус планировщика", callback_data="menu:check_scheduler_status")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def test_daily_schedule(user_id: int, state: FSMContext):
    """Тестирование ежедневного расписания"""
    from utils.notifications import get_notification_manager
    
    await state.clear()
    
    text = "⏳ Отправляю тестовое ежедневное расписание...\n\n"
    
    try:
        notification_manager = get_notification_manager()
        await notification_manager._send_daily_schedule(user_id)
        
        text += "✅ Тестовое уведомление отправлено!\n\n"
        text += "Проверьте, получили ли вы сообщение с расписанием на завтра."
        
    except Exception as e:
        text += f"❌ Ошибка при отправке: {e}\n\n"
        text += "Возможные причины:\n"
        text += "• Расписание на завтра не опубликовано\n"
        text += "• Проблемы с подключением к серверу\n"
        text += "• Ошибка в настройках бота"
    
    btns = [
        [ButtonFactory.back("menu:test_notifications")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def test_lesson_reminder(user_id: int, state: FSMContext):
    """Тестирование напоминания о парах"""
    from utils.notifications import get_notification_manager
    
    await state.clear()
    
    text = "⏳ Отправляю тестовое напоминание о парах...\n\n"
    
    try:
        notification_manager = get_notification_manager()
        # Тестируем с напоминанием за 15 минут
        await notification_manager._send_lesson_reminder(user_id, 15)
        
        text += "✅ Тестовое уведомление отправлено!\n\n"
        text += "Проверьте, получили ли вы напоминание о парах.\n\n"
        text += "⚠️ Примечание: Напоминание отправляется только если:\n"
        text += "• Сегодня не воскресенье\n"
        text += "• Есть расписание на сегодня\n"
        text += "• Текущее время близко к началу пар"
        
    except Exception as e:
        text += f"❌ Ошибка при отправке: {e}\n\n"
        text += "Возможные причины:\n"
        text += "• Сегодня воскресенье\n"
        text += "• Расписание на сегодня не опубликовано\n"
        text += "• Время не подходит для напоминания"
    
    btns = [
        [ButtonFactory.back("menu:test_notifications")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def test_hours_notification(user_id: int, state: FSMContext):
    """Тестирование уведомления о пропусках"""
    from utils.notifications import get_notification_manager
    
    await state.clear()
    
    text = "⏳ Проверяю уведомления о пропусках...\n\n"
    
    try:
        db = DB()
        user = db.get_user_dataclass(user_id)
        settings = db.get_notification_settings(user_id)
        
        if not settings:
            text += "❌ Настройки уведомлений не найдены\n\n"
            text += "Создайте настройки через меню Настройки → Уведомления"
        elif not settings['hours_notification']:
            text += "❌ Уведомления о пропусках отключены\n\n"
            text += "Включите их через меню Настройки → Уведомления"
        else:
            threshold = settings['hours_threshold']
            current_hours = int(user.missed_hours) if user.missed_hours else 0
            
            text += f"📊 <b>Текущее состояние:</b>\n"
            text += f"• Пропущено часов: <b>{current_hours}</b>\n"
            text += f"• Порог уведомления: <b>{threshold}</b>\n"
            text += f"• Уведомления: <b>{'✅ Включены' if settings['hours_notification'] else '❌ Выключены'}</b>\n\n"
            
            if current_hours >= threshold:
                # Отправляем тестовое уведомление
                notification_manager = get_notification_manager()
                message = (
                    f"⚠️ <b>ТЕСТ: Внимание!</b>\n\n"
                    f"У вас накопилось <b>{current_hours}</b> пропущенных часов.\n"
                    f"Это превышает установленный порог ({threshold} часов).\n\n"
                )
                await notification_manager.send_custom_notification(user_id, message)
                
                text += "✅ Тестовое уведомление отправлено!\n"
                text += "Проверьте, получили ли вы предупреждение о пропусках."
            else:
                text += f"ℹ️ Уведомление не будет отправлено, так как количество пропущенных часов ({current_hours}) меньше порога ({threshold}).\n\n"
                text += "Для теста добавьте больше пропущенных часов через /hours"
        
    except Exception as e:
        text += f"❌ Ошибка при проверке: {e}"
    
    btns = [
        [ButtonFactory.back("menu:test_notifications")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def check_scheduler_status(user_id: int, state: FSMContext):
    """Проверка статуса планировщика уведомлений"""
    from utils.notifications import get_notification_manager
    
    await state.clear()
    
    text = "📊 <b>Статус планировщика уведомлений</b>\n\n"
    
    try:
        notification_manager = get_notification_manager()
        
        if notification_manager.scheduler.running:
            text += "✅ Планировщик запущен и работает\n\n"
            
            # Получаем список задач
            jobs = notification_manager.scheduler.get_jobs()
            
            if jobs:
                text += f"📋 <b>Активные задачи ({len(jobs)}):</b>\n\n"
                
                for job in jobs:
                    text += f"• <b>{job.id}</b>\n"
                    text += f"  Следующий запуск: {job.next_run_time.strftime('%d.%m.%Y %H:%M:%S') if job.next_run_time else 'Не запланирован'}\n\n"
            else:
                text += "⚠️ Нет активных задач в планировщике"
        else:
            text += "❌ Планировщик не запущен!\n\n"
            text += "Возможные причины:\n"
            text += "• Бот был перезапущен\n"
            text += "• Произошла ошибка при инициализации\n"
            text += "• Планировщик был остановлен вручную"
        
    except Exception as e:
        text += f"❌ Ошибка при проверке статуса: {e}"
    
    btns = [
        [ButtonFactory.back("menu:test_notifications")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def export_all_data(user_id: int, state: FSMContext):
    """Экспорт всех данных пользователя в PDF"""
    logger.info(f"Запрос экспорта всех данных от пользователя {user_id}")
    
    try:
        # Генерируем PDF
        filepath = await excel_exporter.export_all_user_data(user_id)
        
        # Возвращаем документ
        from aiogram.types import FSInputFile
        document = FSInputFile(filepath)
        
        return {
            "type": "document",
            "document": document,
            "caption": (
                "📥 <b>Экспорт всех данных</b>\n\n"
                "Документ содержит:\n"
                "• Основную информацию профиля\n"
                "• Пропущенные часы\n"
                "• Историю изменений\n"
                "• Настройки уведомлений\n"
                "• Статистику\n\n"
                f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
        }
    
    except Exception as e:
        logger.error(f"Ошибка экспорта данных пользователя {user_id}: {e}", exc_info=True)
        text = (
            "❌ <b>Ошибка экспорта данных</b>\n\n"
            f"Не удалось создать документ: {str(e)}\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )
        btns = [
            [ButtonFactory.back("menu:settings")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# ============================================================================
# НОВЫЕ АДМИНСКИЕ МЕНЮ
# ============================================================================

# Рассылки
@if_admin("user_id")
async def broadcast_main(user_id: int, state: FSMContext):
    """Главное меню рассылок"""
    await state.clear()
    
    # Получаем статистику последних рассылок
    from utils.admin_broadcast import get_broadcast_manager
    broadcast_manager = get_broadcast_manager()
    recent = broadcast_manager.get_broadcast_history(limit=1)
    
    text = "📢 <b>РАССЫЛКА</b>\n\n"
    
    if recent:
        last = recent[0]
        text += f"📊 Последняя рассылка:\n"
        text += f"• Отправлено: {last['success_count']}/{last['total_users']}\n"
        text += f"• Дата: {last['created_at'][:16]}\n\n"
    
    text += "Выберите действие:"
    
    btns = [
        [types.InlineKeyboardButton(text="✉️ Создать рассылку", callback_data="menu:broadcast_create")],
        [types.InlineKeyboardButton(text="📜 История рассылок", callback_data="menu:broadcast_history")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def broadcast_create(user_id: int, state: FSMContext):
    """Создание рассылки - выбор фильтра"""
    await state.clear()
    
    text = "📢 <b>СОЗДАНИЕ РАССЫЛКИ</b>\n\nВыберите аудиторию:"
    
    btns = [
        [types.InlineKeyboardButton(text="👥 Всем пользователям", callback_data="broadcast_filter:all")],
        [types.InlineKeyboardButton(text="📚 По группам", callback_data="broadcast_filter:by_group")],
        [types.InlineKeyboardButton(text="⚡ По активности", callback_data="broadcast_filter:by_activity")],
        [types.InlineKeyboardButton(text="⏰ По пропускам", callback_data="broadcast_filter:by_hours")],
        [types.InlineKeyboardButton(text="🧪 Тестовая (только мне)", callback_data="broadcast_filter:test")],
        [ButtonFactory.back("menu:broadcast_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def broadcast_history(user_id: int, state: FSMContext):
    """История рассылок"""
    await state.clear()
    
    broadcast_manager = get_broadcast_manager()
    broadcasts = broadcast_manager.get_broadcast_history(limit=10)
    
    text = broadcast_manager.format_broadcast_history(broadcasts)
    
    btns = [
        [ButtonFactory.back("menu:broadcast_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# Управление пользователями
@if_admin("user_id")
async def users_management(user_id: int, state: FSMContext):
    """Главное меню управления пользователями"""
    await state.clear()
    
    # Получаем статистику
    db = DB()
    total_users = len(db.get_all("user_id", db.users_table))
    
    # Считаем заблокированных
    db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 1')
    blocked_count = db.cursor.fetchone()[0]
    
    text = "👥 <b>УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ</b>\n\n"
    text += f"📊 Всего: <b>{total_users}</b>\n"
    text += f"🚫 Заблокировано: <b>{blocked_count}</b>\n\n"
    text += "Выберите действие:"
    
    btns = [
        [types.InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="menu:user_search")],
        [types.InlineKeyboardButton(text="📊 Массовые операции", callback_data="menu:user_mass_operations")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def user_search(user_id: int, state: FSMContext):
    """Поиск пользователя"""
    await state.set_state(States.admin_search_user)
    
    text = "🔍 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>\n\n"
    text += "Отправьте:\n"
    text += "• ID пользователя (например: 123456789)\n"
    text += "• Username (например: @username)\n"
    text += "• Номер группы (например: 3191)"
    
    btns = [
        [ButtonFactory.back("menu:users_management")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def user_mass_operations(user_id: int, state: FSMContext):
    """Массовые операции"""
    await state.clear()
    
    text = "📊 <b>МАССОВЫЕ ОПЕРАЦИИ</b>\n\nВыберите действие:"
    
    btns = [
        [types.InlineKeyboardButton(text="🗑️ Очистка неактивных", callback_data="menu:user_cleanup")],
        [types.InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="menu:user_export")],
        [ButtonFactory.back("menu:users_management")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# Аналитика
@if_admin("user_id")
async def analytics_main(user_id: int, state: FSMContext):
    """Главное меню аналитики"""
    await state.clear()
    
    analytics_manager = get_analytics_manager()
    metrics = analytics_manager.get_dashboard_metrics()
    
    text = analytics_manager.format_dashboard(metrics)
    
    btns = [
        [types.InlineKeyboardButton(text="📈 Графики", callback_data="menu:analytics_charts")],
        [types.InlineKeyboardButton(text="📥 Экспорт аналитики", callback_data="menu:analytics_export")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def analytics_charts(user_id: int, state: FSMContext):
    """Меню графиков"""
    await state.clear()
    
    text = "📈 <b>ГРАФИКИ</b>\n\n"
    text += "Выберите тип графика для просмотра:"
    
    btns = [
        [
            types.InlineKeyboardButton(text="📈 Рост пользователей", callback_data="chart:user_growth"),
            types.InlineKeyboardButton(text="⚡ Активность", callback_data="chart:activity")
        ],
        [types.InlineKeyboardButton(text="📉 Распределение пропусков", callback_data="chart:hours_distribution")],
        [ButtonFactory.back("menu:analytics_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# Мониторинг
@if_admin("user_id")
async def monitoring_main(user_id: int, state: FSMContext):
    """Главное меню мониторинга"""
    await state.clear()
    
    # Получаем краткую статистику
    from utils.admin_monitoring import get_system_monitor
    system_monitor = get_system_monitor()
    health = system_monitor.check_health()
    
    status_emoji = {
        'healthy': '✅',
        'warning': '⚠️',
        'critical': '🚨',
        'error': '❌'
    }
    
    emoji = status_emoji.get(health['status'], '❓')
    
    text = "📝 <b>МОНИТОРИНГ</b>\n\n"
    text += f"{emoji} Статус системы: <b>{health['status'].upper()}</b>\n\n"
    text += "Выберите раздел:"
    
    btns = [
        [
            types.InlineKeyboardButton(text="📋 Логи", callback_data="menu:admin_logs"),
            types.InlineKeyboardButton(text="⚠️ Ошибки", callback_data="menu:error_monitoring")
        ],
        [
            types.InlineKeyboardButton(text="⚙️ Система", callback_data="menu:system_status"),
            types.InlineKeyboardButton(text="✅ Здоровье", callback_data="menu:health_check")
        ],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def admin_logs(user_id: int, state: FSMContext):
    """Журнал действий администратора"""
    await state.clear()
    
    admin_logger = get_admin_logger()
    logs = admin_logger.get_logs(limit=20, days=7)
    
    text = admin_logger.format_logs_for_display(logs)
    
    btns = [
        [types.InlineKeyboardButton(text="📥 Экспорт логов", callback_data="menu:logs_export")],
        [ButtonFactory.back("menu:monitoring_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def error_monitoring(user_id: int, state: FSMContext):
    """Мониторинг ошибок"""
    await state.clear()
    
    error_logger = get_error_logger()
    errors = error_logger.get_recent_errors(limit=10)
    
    text = error_logger.format_errors_for_display(errors)
    text += "\n"
    
    # Добавляем статистику
    stats = error_logger.get_error_stats(days=1)
    text += f"\n<b>Статистика за 24 часа:</b>\n"
    text += f"Всего ошибок: <b>{sum(stats.values())}</b>\n"
    
    btns = [
        [types.InlineKeyboardButton(text="📊 Статистика ошибок", callback_data="menu:error_stats")],
        [ButtonFactory.back("menu:monitoring_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def system_status(user_id: int, state: FSMContext):
    """Статус системы"""
    await state.clear()
    
    system_monitor = get_system_monitor()
    status = system_monitor.get_system_status()
    
    text = system_monitor.format_system_status(status)
    
    # Добавляем статус планировщика
    scheduler_status = system_monitor.check_scheduler_status()
    text += "\n" + system_monitor.format_scheduler_status(scheduler_status)
    
    btns = [
        [ButtonFactory.back("menu:monitoring_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def health_check(user_id: int, state: FSMContext):
    """Проверка здоровья системы"""
    await state.clear()
    
    system_monitor = get_system_monitor()
    health = system_monitor.check_health()
    
    text = system_monitor.format_health_check(health)
    
    btns = [
        [ButtonFactory.back("menu:monitoring_main")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# Настройки бота
@if_admin("user_id")
async def bot_settings(user_id: int, state: FSMContext):
    """Настройки бота"""
    await state.clear()
    
    maintenance = get_maintenance_mode()
    admin_notif = get_admin_notifications()
    
    text = "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n"
    
    # Режим обслуживания
    maintenance_status = "✅ Включен" if maintenance.is_enabled() else "❌ Выключен"
    text += f"<b>Режим обслуживания:</b> {maintenance_status}\n\n"
    
    # Уведомления админу
    text += admin_notif.get_settings_text()
    
    btns = [
        [types.InlineKeyboardButton(
            text="🔧 Режим обслуживания",
            callback_data="menu:toggle_maintenance"
        )],
        [types.InlineKeyboardButton(
            text="🔔 Настройки уведомлений",
            callback_data="menu:admin_notifications_settings"
        )],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


@if_admin("user_id")
async def admin_notifications_settings(user_id: int, state: FSMContext):
    """Настройки уведомлений администратору"""
    await state.clear()
    
    admin_notif = get_admin_notifications()
    
    text = admin_notif.get_settings_text()
    text += "\n\n💡 Используйте кнопки ниже для изменения настроек:"
    
    # Получаем текущие настройки
    enabled = admin_notif.is_enabled()
    
    btns = [
        [types.InlineKeyboardButton(
            text=f"{'✅' if enabled else '❌'} Уведомления {'включены' if enabled else 'выключены'}",
            callback_data="toggle_admin_notif:main"
        )],
        [types.InlineKeyboardButton(
            text="🚨 Критические ошибки",
            callback_data="toggle_admin_notif:critical_errors"
        )],
        [types.InlineKeyboardButton(
            text="👤 Новые пользователи",
            callback_data="toggle_admin_notif:new_users"
        )],
        [types.InlineKeyboardButton(
            text="⚠️ Превышение порога ошибок",
            callback_data="toggle_admin_notif:error_threshold"
        )],
        [types.InlineKeyboardButton(
            text="📅 Проблемы с расписанием",
            callback_data="toggle_admin_notif:schedule_problems"
        )],
        [types.InlineKeyboardButton(
            text="💿 Заполнение диска",
            callback_data="toggle_admin_notif:disk_space"
        )],
        [ButtonFactory.back("menu:bot_settings")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


# Быстрые действия
@if_admin("user_id")
async def quick_actions(user_id: int, state: FSMContext):
    """Быстрые действия"""
    await state.clear()
    
    text = "⚡ <b>БЫСТРЫЕ ДЕЙСТВИЯ</b>\n\n"
    text += "Выполнение системных операций:"
    
    btns = [
        [
            types.InlineKeyboardButton(text="🔄 Перезапуск планировщика", callback_data="quick:restart_scheduler"),
            types.InlineKeyboardButton(text="🗑️ Очистить кэш", callback_data="quick:clear_cache")
        ],
        [
            types.InlineKeyboardButton(text="📥 Обновить расписания", callback_data="quick:update_schedules"),
            types.InlineKeyboardButton(text="✅ Проверить статус", callback_data="quick:check_status")
        ],
        [types.InlineKeyboardButton(text="🔔 Тестовое уведомление", callback_data="quick:test_notification")],
        [ButtonFactory.back("menu:admin")]
    ]
    
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
