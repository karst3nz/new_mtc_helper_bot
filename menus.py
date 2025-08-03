import config
from utils.decorators import if_admin
from rasp import Rasp
from log import create_logger
from db import DB
from state import States
from datetime import datetime

from utils.utils import format_and_return_columns
logger = create_logger(__name__, level="DEBUG")

async def rasp(user_id: int, date: str = None, _get_new: bool = False):
    group, sec_group = DB().get_user_groups(user_id)
    date = date if date is not None else datetime.today().date().strftime("%d_%m_%Y")
    rasp = Rasp(date)
    return await rasp.create_rasp_msg(
        group=group,
        sec_group=sec_group,
        _get_new=_get_new
    )


from aiogram import types
from aiogram.fsm.context import FSMContext
async def start(user_id: int, state: FSMContext): 
    if DB().is_exists(user_id) is False:
        text = "👋 Привет! Я бот для просмотра расписания занятий.\n\n📝 Для начала работы, пожалуйста, отправьте номер вашей группы:"
        await state.set_state(States.first_reg_group)
        return text, types.InlineKeyboardMarkup(inline_keyboard=[[]])
    else:
        text = "🎓 Главное меню\n\nВыберите нужный раздел:"
        btns = [
            [types.InlineKeyboardButton(text="📅 Расписание", callback_data="menu:rasp")],
            [types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")]
        ]
        if str(user_id) == str(config.ADMIN_ID): btns += [[types.InlineKeyboardButton(text='ADMIN', callback_data="menu:admin")]]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def skip_sec_group(user_id: int, state: FSMContext):
    state_data = await state.get_data()
    group = state_data.get("group", "0000")
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
    text = f"⚙️ Настройки профиля\n\n📋 Основная группа: <b>{group}</b>"
    if sec_group is not None:
        text += f"\n📋 Дополнительная группа: <b>{sec_group}</b>"
    else:
        text += "\n📋 Дополнительная группа: <i>не указана</i>"
    
    btns = [
        [types.InlineKeyboardButton(text="✏️ Изменить основную группу", callback_data="menu:change_main_group")],
        [types.InlineKeyboardButton(text="✏️ Изменить доп. группу" if sec_group is not None else "➕ Добавить доп. группу", callback_data="menu:change_sec_group")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="menu:start")]
    ]
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)


async def change_main_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
    text = f"✏️ Изменение основной группы\n\n📋 Текущая группа: <b>{group}</b>\n\n📝 Отправьте новый номер группы:"
    btns = [
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="menu:settings")]
    ]
    await state.set_state(States.change_main_group)
    return text, types.InlineKeyboardMarkup(inline_keyboard=btns)

async def change_sec_group(user_id: int, state: FSMContext):
    db = DB()
    group, sec_group = db.get_user_groups(user_id)
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
    db_all_users = ('Краткая сводка по БД:\n'
                    f'Количество пользователей: {len(db.get_all("id", db.users_table))}\n\n'
                    # f'Количество бесед: {len(db.get_all("tg_group_id", db.users_table))}\n'
                    # f'Общее количество участников в беседах: '
                    # f'{sum(int(db.get_all("count_members", db.users_table)))}\n'
                    )
    border = "*________________________________________*"
    group_info_start = 'Информация по группам:'
    group = db.get_all("group_id", db.users_table)
    final_list_group = []
    for item in config.groups:
        count_of_ones = len([x for x in group if str(x) == item])
        if count_of_ones == 0:
            continue
        else:
            final_list_group.append(f"{item} - {count_of_ones}")
    final_list_group.sort(key=lambda x: int(x.split(' - ')[1]), reverse=True)
    group_text = ''
    for x in final_list_group:
        group_text += x + "\n"
    y = format_and_return_columns(group_text)
    final_text = f"{db_all_users}" + f"{border}\n" + f"{group_info_start}\n" + f"{y}"
    db_info_buttons = [
        [types.InlineKeyboardButton(text="Выгрузить информацию по группе", callback_data="menu:db_group")],
        [types.InlineKeyboardButton(text="Выгрузить информацию по человеку", callback_data="menu:db_user")],
        [types.InlineKeyboardButton(text="Назад", callback_data="menu:admin")]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=db_info_buttons)
    return final_text, reply_markup

@if_admin("user_id")
async def db_group(user_id: int, state: FSMContext):
    await state.set_state(States.db_group_info)
    return 'group_id?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])


@if_admin("user_id")
async def db_user(user_id: int, state: FSMContext):
    await state.set_state(States.db_user_info)
    return 'user_id?', types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="< Назад", callback_data="menu:database")]])
