from aiogram.fsm.state import StatesGroup, State


class States(StatesGroup):
    
    """
    Класс для FSM
    """
    first_reg_group = State()
    sec_reg_group = State()
    change_main_group = State()
    change_sec_group = State()