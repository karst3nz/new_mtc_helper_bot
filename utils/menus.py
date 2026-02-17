import re
from typing import Literal
import config
from utils.decorators import if_admin
from utils.rasp import Rasp
from utils.log import create_logger
from utils.db import DB
from utils.state import States
from datetime import datetime, timedelta

from utils.utils import format_and_return_columns, get_lesson_time
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
    return text, btns


from aiogram import types
from aiogram.fsm.context import FSMContext
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
            [types.InlineKeyboardButton(text="🔔 Расписание звонков", callback_data="menu:lesson_schedule?('True')")],
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
        return '✅' if mode in userDC.show_missed_hours_mode else '❌'

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
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:start")]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_main_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    await state.clear()
    text = f"✏️ Изменение основной группы\n\n📋 Текущая группа: <b>{group}</b>\n\n📝 Отправьте новый номер группы:"
    btns = [
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="menu:settings")]
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
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="menu:settings")]
    ]
    await state.set_state(States.change_sec_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def delete_sec_group(user_id: int, state: FSMContext):
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
    text = "🛠️ ADMIN"
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="📢 Рассылка", callback_data="menu:ad")],
        [types.InlineKeyboardButton(text="🗄️ База Данных", callback_data="menu:database")],
        [types.InlineKeyboardButton(text="< Назад", callback_data="menu:start")]
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
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:admin")]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=db_info_buttons)
    return final_text, reply_markup

@if_admin("user_id")
async def db_user(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.db_user_info)
    return '🔎 user_id?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])

@if_admin("user_id")
async def db_group(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.db_group_info)
    return '🔎 group?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])


@if_admin("user_id")
async def ad(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.ad_msg)
    return "✉️ Отправь текст", types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Отмена", callback_data="menu:admin")]])


async def add_missing_hours(user_id: int, state: FSMContext):
    await state.clear()
    db = DB()
    user = db.get_user_dataclass(user_id)
    text = (
        f"⏰ У тебя сейчас пропущенно {user.missed_hours}ч.\n\n"
        "✍️ Отправь, сколько часов ты уже пропустил. Я их прибавлю к текущим"
    )
    btns = [
        [types.InlineKeyboardButton(text="🗑️ Очистить", callback_data="menu:clear_missing_hours")],
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="delete_msg")]
    ]
    await state.set_state(States.add_missing_hours)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def clear_missing_hours(user_id: int, state: FSMContext):
    await state.clear()
    db = DB()
    user = db.get_user_dataclass(user_id)
    prev = user.missed_hours
    btns = [
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    try:
        db.cursor.execute("UPDATE users SET missed_hours = 0 WHERE user_id = ?", (user_id,))
        db.conn.commit()
        text = f"✅ Пропущенные часы успешно очищены!\nЗначение до очистки: <b>{prev}</b>"
    except Exception as e:
        text = f"❌ Произошла ошибка при очистке пропущенных часов: {e}"
    finally:
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
            callback_data="menu:missed_hours_mode?('start')"
        )],
        [types.InlineKeyboardButton(
            text="Просмотр расписания" + (" ❌" if show_missed_hours_mode is None or 'rasp' not in show_missed_hours_mode else " ✅️"),
            callback_data="menu:missed_hours_mode?('rasp')"
        )],
        [types.InlineKeyboardButton(
            text="Новое расписание" + (" ❌" if show_missed_hours_mode is None or 'newRasp' not in show_missed_hours_mode else " ✅️"),
            callback_data="menu:missed_hours_mode?('newRasp')"
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
        [types.InlineKeyboardButton(text=f"{'❌' if condition is False else '✅️'} Закреплять новое расписание", callback_data="menu:group_settings?('pin_new_rasp')")],
        [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data="menu:change_GROUP_group")], # по другому не придумал xD
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    return "⚙️ Настройки", types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_GROUP_group(id: int, state: FSMContext):
    db = DB()
    try:
        group = db.cursor.execute('SELECT "group" FROM groups WHERE id = ?', (id,)).fetchone()[0]
    except Exception:
        return "❌ Не удалось найти вашу группу в базе, попробуйте передобавить бота", types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]])
    text = f"""
✏️ Изменение группы

📋 Текущая группа: {group}

📝 Отправьте новый номер группы:
        """
    await state.set_state(States.GROUP_change_group)
    await state.update_data(id=id)
    return text, types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]]) 



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

    btns = [[types.InlineKeyboardButton(text="◀️ Назад", callback_data=f"menu:rasp?{(date, False, show_lesson_time)}")]]
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
        [types.InlineKeyboardButton(text=get_btn_text("1"), callback_data="menu:smena_edit?('1')")],
        [types.InlineKeyboardButton(text=get_btn_text("2"), callback_data="menu:smena_edit?('2')")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")]
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
        [types.InlineKeyboardButton(text=f"✅️ Пн-Пт" if weekday == "True" else f"Пн-Пт", callback_data="menu:lesson_schedule?('True')")],
        [types.InlineKeyboardButton(text=f"✅️ Суббота" if weekday == "False" else f"Суббота", callback_data="menu:lesson_schedule?('False')")],
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
