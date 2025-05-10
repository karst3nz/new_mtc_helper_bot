from aiogram.fsm.state import StatesGroup, State


class States(StatesGroup):
    
    """
    Класс для FSM
    """
    _input = State()