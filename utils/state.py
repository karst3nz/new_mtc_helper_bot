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
    GROUP_reg_group = State()
    GROUP_change_group = State()
    
    # Новые состояния для улучшенной админ-панели
    # Рассылки
    broadcast_message = State()
    broadcast_filter_groups = State()
    broadcast_filter_activity_days = State()
    broadcast_filter_hours_min = State()
    broadcast_filter_hours_max = State()
    
    # Управление пользователями
    admin_search_user = State()
    admin_user_send_message = State()
    admin_user_change_group = State()
    admin_user_change_sec_group = State()
    admin_cleanup_days = State()
    admin_block_reason = State()
    
    # Логи и мониторинг
    admin_logs_days = State()
    admin_export_logs_start = State()
    admin_export_logs_end = State()