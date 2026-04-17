"""
Режим обслуживания для бота
"""
from typing import Optional
from utils.db import DB
from utils.log import create_logger
from utils.admin_logger import get_admin_logger

logger = create_logger(__name__)


class MaintenanceMode:
    """Управление режимом обслуживания"""
    
    SETTING_KEY = 'maintenance_mode'
    
    def __init__(self):
        self.db = DB()
        self.admin_logger = get_admin_logger()
    
    def is_enabled(self) -> bool:
        """
        Проверить, включен ли режим обслуживания
        
        Returns:
            True если включен
        """
        try:
            self.db.cursor.execute(
                'SELECT value FROM bot_settings WHERE key = ?',
                (self.SETTING_KEY,)
            )
            row = self.db.cursor.fetchone()
            
            if row:
                return row[0] == '1' or row[0].lower() == 'true'
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check maintenance mode: {e}")
            return False
    
    def enable(self, admin_id: int, reason: Optional[str] = None) -> bool:
        """
        Включить режим обслуживания
        
        Args:
            admin_id: ID администратора
            reason: Причина включения
        
        Returns:
            True если успешно
        """
        try:
            # Устанавливаем настройку
            self.db.cursor.execute(
                '''INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))''',
                (self.SETTING_KEY, '1')
            )
            
            # Сохраняем причину если указана
            if reason:
                self.db.cursor.execute(
                    '''INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                       VALUES (?, ?, datetime('now'))''',
                    ('maintenance_reason', reason)
                )
            
            self.db.conn.commit()
            
            # Логируем действие
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='maintenance_on',
                details={'reason': reason}
            )
            
            logger.info(f"Maintenance mode enabled by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable maintenance mode: {e}")
            return False
    
    def disable(self, admin_id: int) -> bool:
        """
        Выключить режим обслуживания
        
        Args:
            admin_id: ID администратора
        
        Returns:
            True если успешно
        """
        try:
            # Устанавливаем настройку
            self.db.cursor.execute(
                '''INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))''',
                (self.SETTING_KEY, '0')
            )
            
            # Удаляем причину
            self.db.cursor.execute(
                'DELETE FROM bot_settings WHERE key = ?',
                ('maintenance_reason',)
            )
            
            self.db.conn.commit()
            
            # Логируем действие
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='maintenance_off'
            )
            
            logger.info(f"Maintenance mode disabled by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable maintenance mode: {e}")
            return False
    
    def get_reason(self) -> Optional[str]:
        """
        Получить причину включения режима обслуживания
        
        Returns:
            Причина или None
        """
        try:
            self.db.cursor.execute(
                'SELECT value FROM bot_settings WHERE key = ?',
                ('maintenance_reason',)
            )
            row = self.db.cursor.fetchone()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Failed to get maintenance reason: {e}")
            return None
    
    def check_access(self, user_id: int) -> bool:
        """
        Проверить, имеет ли пользователь доступ в режиме обслуживания
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если доступ разрешен
        """
        from config import ADMIN_ID
        
        # Админ всегда имеет доступ
        if str(user_id) == str(ADMIN_ID):
            return True
        
        # Если режим обслуживания выключен, доступ есть у всех
        if not self.is_enabled():
            return True
        
        # В режиме обслуживания доступ только у админа
        return False
    
    def get_maintenance_message(self) -> str:
        """
        Получить сообщение для пользователей в режиме обслуживания
        
        Returns:
            Текст сообщения
        """
        reason = self.get_reason()
        
        text = "🔧 <b>Бот находится на техническом обслуживании</b>\n\n"
        
        if reason:
            text += f"<i>{reason}</i>\n\n"
        
        text += "Пожалуйста, попробуйте позже."
        
        return text


# Глобальный экземпляр
_maintenance_mode = None


def get_maintenance_mode() -> MaintenanceMode:
    """Получить глобальный экземпляр MaintenanceMode"""
    global _maintenance_mode
    if _maintenance_mode is None:
        _maintenance_mode = MaintenanceMode()
    return _maintenance_mode


def is_maintenance_mode() -> bool:
    """Быстрая проверка режима обслуживания"""
    return get_maintenance_mode().is_enabled()


def check_maintenance_access(user_id: int) -> bool:
    """Быстрая проверка доступа в режиме обслуживания"""
    return get_maintenance_mode().check_access(user_id)
