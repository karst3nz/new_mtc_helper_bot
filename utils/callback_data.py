"""
Безопасная система сериализации callback данных для Telegram bot
Заменяет небезопасный ast.literal_eval() на JSON-based подход
"""
import json
import hashlib
from typing import Any, Optional
from utils.log import create_logger

logger = create_logger(__name__)


class CallbackData:
    """Безопасная сериализация callback данных"""
    
    # Максимальная длина callback_data в Telegram
    MAX_CALLBACK_LENGTH = 64
    
    @staticmethod
    def encode(action: str, *args) -> str:
        """
        Кодирует действие и аргументы в безопасную строку
        
        Args:
            action: Название функции меню
            *args: Аргументы для функции
            
        Returns:
            Закодированная строка для callback_data
            
        Example:
            encode("rasp", "01_04_2026", False, True)
            -> "menu:rasp?[\"01_04_2026\",false,true]"
        """
        if not args:
            return f"menu:{action}"
        
        try:
            # Сериализуем аргументы в JSON
            args_json = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
            
            # Проверяем длину
            callback_str = f"menu:{action}?{args_json}"
            
            if len(callback_str) <= CallbackData.MAX_CALLBACK_LENGTH:
                return callback_str
            
            # Если слишком длинно, используем хеш
            args_hash = hashlib.md5(args_json.encode()).hexdigest()[:8]
            logger.warning(f"Callback data too long, using hash: {action} with {len(args)} args")
            return f"menu:{action}?h:{args_hash}"
            
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to encode callback data: {e}")
            return f"menu:{action}"
    
    @staticmethod
    def decode(callback_data: str) -> tuple[str, tuple]:
        """
        Декодирует callback_data в действие и аргументы
        
        Args:
            callback_data: Строка callback_data
            
        Returns:
            Кортеж (action, args)
            
        Example:
            decode("menu:rasp?[\"01_04_2026\",false,true]")
            -> ("rasp", ("01_04_2026", False, True))
        """
        if not callback_data.startswith("menu:"):
            return "", ()
        
        menu_data = callback_data[len("menu:"):]
        
        if "?" not in menu_data:
            return menu_data, ()
        
        action, raw_args = menu_data.split("?", 1)
        raw_args = raw_args.strip()
        
        if not raw_args:
            return action, ()
        
        # Проверяем, не хеш ли это
        if raw_args.startswith("h:"):
            logger.warning(f"Received hashed callback data for {action}")
            return action, ()
        
        try:
            # Пытаемся декодировать JSON
            args_list = json.loads(raw_args)
            
            # Преобразуем в кортеж
            if isinstance(args_list, list):
                return action, tuple(args_list)
            else:
                return action, (args_list,)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to decode callback data: {e}, raw: {raw_args}")
            return action, ()
    
    @staticmethod
    def validate(callback_data: str) -> bool:
        """
        Проверяет валидность callback_data
        
        Args:
            callback_data: Строка для проверки
            
        Returns:
            True если валидна, False иначе
        """
        if not isinstance(callback_data, str):
            return False
        
        if len(callback_data) > CallbackData.MAX_CALLBACK_LENGTH:
            return False
        
        if not callback_data.startswith("menu:"):
            # Разрешаем специальные callback
            return callback_data in ["delete_msg", "check_pin_rights"] or \
                   callback_data.startswith(("ad_", "calendar:"))
        
        try:
            action, args = CallbackData.decode(callback_data)
            return bool(action)
        except Exception:
            return False
