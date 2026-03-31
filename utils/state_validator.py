"""
Валидация FSM состояний для безопасной работы с данными состояний
"""
from typing import Optional, List, Any
from aiogram.fsm.context import FSMContext
from functools import wraps
from utils.log import create_logger

logger = create_logger(__name__)


async def validate_state_data(state: FSMContext, required_keys: List[str]) -> Optional[dict]:
    """
    Проверяет наличие обязательных ключей в данных состояния
    
    Args:
        state: FSM контекст
        required_keys: Список обязательных ключей
        
    Returns:
        Словарь с данными состояния или None если валидация не прошла
    """
    try:
        data = await state.get_data()
        
        if not data:
            logger.warning("State data is empty")
            return None
        
        # Проверяем наличие всех обязательных ключей
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            logger.warning(f"Missing required keys in state data: {missing_keys}")
            return None
        
        # Проверяем, что значения не None
        none_keys = [key for key in required_keys if data.get(key) is None]
        
        if none_keys:
            logger.warning(f"Keys with None values in state data: {none_keys}")
            return None
        
        return data
        
    except Exception as e:
        logger.error(f"Error validating state data: {e}")
        return None


def require_state_data(*required_keys: str):
    """
    Декоратор для автоматической валидации данных состояния
    
    Args:
        *required_keys: Обязательные ключи в state data
        
    Example:
        @require_state_data("group", "user_id")
        async def my_handler(msg: Message, state: FSMContext):
            data = await state.get_data()
            # data гарантированно содержит "group" и "user_id"
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Ищем FSMContext в аргументах
            state = None
            for arg in args:
                if isinstance(arg, FSMContext):
                    state = arg
                    break
            
            if state is None:
                state = kwargs.get('state')
            
            if state is None:
                logger.error(f"FSMContext not found in {func.__name__} arguments")
                raise ValueError("FSMContext is required for this handler")
            
            # Валидируем данные состояния
            data = await validate_state_data(state, list(required_keys))
            
            if data is None:
                logger.error(f"State validation failed in {func.__name__}")
                # Очищаем невалидное состояние
                await state.clear()
                raise ValueError(f"Required state data missing: {required_keys}")
            
            # Вызываем оригинальную функцию
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def safe_get_state_value(state: FSMContext, key: str, default: Any = None) -> Any:
    """
    Безопасно получает значение из state data с дефолтным значением
    
    Args:
        state: FSM контекст
        key: Ключ для получения
        default: Значение по умолчанию
        
    Returns:
        Значение из state или default
    """
    try:
        data = await state.get_data()
        return data.get(key, default)
    except Exception as e:
        logger.error(f"Error getting state value for key '{key}': {e}")
        return default


async def safe_update_state(state: FSMContext, **kwargs) -> bool:
    """
    Безопасно обновляет данные состояния
    
    Args:
        state: FSM контекст
        **kwargs: Данные для обновления
        
    Returns:
        True если успешно, False иначе
    """
    try:
        await state.update_data(**kwargs)
        return True
    except Exception as e:
        logger.error(f"Error updating state data: {e}")
        return False


class StateValidator:
    """Класс для валидации различных типов данных в состоянии"""
    
    @staticmethod
    def validate_group_id(group_id: Any) -> bool:
        """Проверяет валидность номера группы"""
        if not group_id:
            return False
        
        group_str = str(group_id)
        
        # Проверяем, что это число из 4 цифр
        if not group_str.isdigit():
            return False
        
        if len(group_str) != 4:
            return False
        
        return True
    
    @staticmethod
    def validate_user_id(user_id: Any) -> bool:
        """Проверяет валидность user_id"""
        if not user_id:
            return False
        
        try:
            uid = int(user_id)
            return uid > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_date(date_str: Any) -> bool:
        """Проверяет валидность даты в формате DD_MM_YYYY"""
        if not date_str:
            return False
        
        try:
            parts = str(date_str).split('_')
            if len(parts) != 3:
                return False
            
            day, month, year = map(int, parts)
            
            # Базовая проверка диапазонов
            if not (1 <= day <= 31):
                return False
            if not (1 <= month <= 12):
                return False
            if not (2020 <= year <= 2030):
                return False
            
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def validate_hours(hours: Any) -> bool:
        """Проверяет валидность количества часов"""
        try:
            h = int(hours)
            return 0 <= h <= 1000  # Разумный диапазон
        except (ValueError, TypeError):
            return False
