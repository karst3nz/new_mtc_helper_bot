from aiogram.fsm.state import StatesGroup, State


class States(StatesGroup):
    
    """
    Класс для FSM
    """
    first_reg_group = State()
    sec_reg_group = State()
    change_main_group = State()
    change_sec_group = State()
    db_group_info = State()
    db_user_info = State()
    ad_msg = State()
    ad_confirm = State()
    add_missing_hours = State()