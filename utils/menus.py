import re
import config
from utils.decorators import if_admin
from utils.rasp import Rasp
from utils.log import create_logger
from utils.db import DB
from utils.state import States
from datetime import datetime

from utils.utils import format_and_return_columns
logger = create_logger(__name__)

async def rasp(user_id: int, date: str = None, _get_new: bool = False):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
    rasp = Rasp(date)
    text, btns = await rasp.create_rasp_msg(
        group=group,
        sec_group=sec_group,
        _get_new=_get_new
    )
    user = db.get_user_dataclass(user_id)
    if "rasp" in user.show_missed_hours_mode: text += f"\n⏰ У тебя сейчас <b>{user.missed_hours}</b> пропущенных часов."
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
        if "start" in (user.show_missed_hours_mode or ""):
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
            [types.InlineKeyboardButton(text="📅 Расписание", callback_data="menu:rasp")],
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
    group, sec_group = db.get_user_groups(user_id)
    await state.clear()
    text = f"⚙️ Настройки профиля\n\n📋 Основная группа: <b>{group}</b>"
    if sec_group is not None:
        text += f"\n📋 Дополнительная группа: <b>{sec_group}</b>"
    else:
        text += "\n📋 Дополнительная группа: <i>не указана</i>"
    
    btns = [
        [types.InlineKeyboardButton(text="✏️ Изменить основную группу", callback_data="menu:change_main_group")],
        [types.InlineKeyboardButton(text="✏️ Изменить доп. группу" if sec_group is not None else "➕ Добавить доп. группу", callback_data="menu:change_sec_group")],
        [types.InlineKeyboardButton(text="Отображение пропущенных часов", callback_data="menu:missed_hours_mode")],
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
    text = "ADMIN"
    await state.clear()
    btns = [
        [types.InlineKeyboardButton(text="Рассылка", callback_data="menu:ad")],
        [types.InlineKeyboardButton(text="База Данных", callback_data="menu:database")],
        [types.InlineKeyboardButton(text="Ручная отправка расписания", callback_data="menu:send_rasp")],
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
        [types.InlineKeyboardButton(text="Выгрузить информацию по группе", callback_data="menu:db_group")],
        [types.InlineKeyboardButton(text="Выгрузить информацию по человеку", callback_data="menu:db_user")],
        [types.InlineKeyboardButton(text="Назад", callback_data="menu:admin")]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=db_info_buttons)
    return final_text, reply_markup

# @if_admin("user_id")
# async def db_group(user_id: int, state: FSMContext):
#     await state.clear()
#     await state.set_state(States.db_group_info)
#     return 'group_id?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])


@if_admin("user_id")
async def db_user(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.db_user_info)
    return 'user_id?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])


@if_admin("user_id")
async def ad(user_id: int, state: FSMContext):
    await state.clear()
    await state.set_state(States.ad_msg)
    return "Отправь текст", types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Отмена", callback_data="menu:admin")]])


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
    return "Показ пропущенных часов", types.InlineKeyboardMarkup(inline_keyboard=btns)


async def group_settings(user_id: int, state: FSMContext):
    btns = [
        [types.InlineKeyboardButton(text="✏️ Изменить группу", callback_data="menu:change_GROUP_group")], # по другому не придумал xD
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ]
    return "Настройки", types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_GROUP_group(id: int, state: FSMContext):
    db = DB()
    try:
        group = db.cursor.execute('SELECT "group" FROM groups WHERE id = ?', (id,)).fetchone()[0]
    except Exception:
        return "Не удалось найти вашу группу в базе, попробуйте передобавить бота", types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]])
    text = f"""
✏️ Изменение группы

📋 Текущая группа: {group}

📝 Отправьте новый номер группы:
        """
    await state.set_state(States.GROUP_change_group)
    await state.update_data(id=id)
    return text, types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]]) 