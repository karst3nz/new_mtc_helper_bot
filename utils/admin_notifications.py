"""
Система уведомлений для администратора
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from utils.db import DB
from utils.log import create_logger
from config import bot, ADMIN_ID

logger = create_logger(__name__)


class AdminNotifications:
    """Менеджер уведомлений администратору"""
    
    def __init__(self):
        self.db = DB()
        self._init_settings()
    
    def _init_settings(self):
        """Инициализация настроек уведомлений"""
        try:
            # Проверяем существование настроек
            self.db.cursor.execute(
                'SELECT value FROM bot_settings WHERE key = ?',
                ('admin_notifications_enabled',)
            )
            
            if not self.db.cursor.fetchone():
                # Создаем настройки по умолчанию
                default_settings = {
                    'admin_notifications_enabled': '1',
                    'notify_critical_errors': '1',
                    'notify_new_users': '0',
                    'notify_error_threshold': '1',
                    'notify_schedule_problems': '1',
                    'notify_disk_space': '1',
                    'error_threshold_count': '10',
                    'error_threshold_minutes': '60'
                }
                
                for key, value in default_settings.items():
                    self.db.cursor.execute(
                        '''INSERT OR IGNORE INTO bot_settings (key, value, updated_at)
                           VALUES (?, ?, datetime('now'))''',
                        (key, value)
                    )
                
                self.db.conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to init admin notification settings: {e}")
    
    def is_enabled(self) -> bool:
        """Проверить, включены ли уведомления"""
        try:
            self.db.cursor.execute(
                'SELECT value FROM bot_settings WHERE key = ?',
                ('admin_notifications_enabled',)
            )
            row = self.db.cursor.fetchone()
            return row and row[0] == '1'
        except:
            return True
    
    def get_setting(self, key: str) -> Optional[str]:
        """Получить значение настройки"""
        try:
            self.db.cursor.execute(
                'SELECT value FROM bot_settings WHERE key = ?',
                (key,)
            )
            row = self.db.cursor.fetchone()
            return row[0] if row else None
        except:
            return None
    
    def set_setting(self, key: str, value: str) -> bool:
        """Установить значение настройки"""
        try:
            self.db.cursor.execute(
                '''INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))''',
                (key, value)
            )
            self.db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    async def notify_critical_error(self, error_type: str, error_message: str, 
                                    traceback: Optional[str] = None):
        """
        Уведомление о критической ошибке
        
        Args:
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
            traceback: Traceback
        """
        if not self.is_enabled() or self.get_setting('notify_critical_errors') != '1':
            return
        
        try:
            text = "🚨 <b>КРИТИЧЕСКАЯ ОШИБКА</b>\n\n"
            text += f"<b>Тип:</b> {error_type}\n"
            text += f"<b>Сообщение:</b> {error_message}\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            
            if traceback:
                # Ограничиваем длину traceback
                tb_preview = traceback[:500]
                if len(traceback) > 500:
                    tb_preview += "..."
                text += f"\n<b>Traceback:</b>\n<code>{tb_preview}</code>"
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info("Critical error notification sent to admin")
            
        except Exception as e:
            logger.error(f"Failed to send critical error notification: {e}")
    
    async def notify_new_user(self, user_id: int, username: Optional[str], group: str):
        """
        Уведомление о новом пользователе
        
        Args:
            user_id: ID пользователя
            username: Username
            group: Группа
        """
        if not self.is_enabled() or self.get_setting('notify_new_users') != '1':
            return
        
        try:
            text = "👤 <b>Новый пользователь</b>\n\n"
            text += f"<b>ID:</b> <code>{user_id}</code>\n"
            text += f"<b>Username:</b> @{username or 'не указан'}\n"
            text += f"<b>Группа:</b> {group}\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info(f"New user notification sent to admin: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send new user notification: {e}")
    
    async def notify_error_threshold(self, error_count: int, period_minutes: int):
        """
        Уведомление о превышении порога ошибок
        
        Args:
            error_count: Количество ошибок
            period_minutes: Период в минутах
        """
        if not self.is_enabled() or self.get_setting('notify_error_threshold') != '1':
            return
        
        try:
            text = "⚠️ <b>ПРЕВЫШЕН ПОРОГ ОШИБОК</b>\n\n"
            text += f"<b>Количество ошибок:</b> {error_count}\n"
            text += f"<b>За период:</b> {period_minutes} минут\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            text += "Рекомендуется проверить логи и состояние системы."
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info("Error threshold notification sent to admin")
            
        except Exception as e:
            logger.error(f"Failed to send error threshold notification: {e}")
    
    async def notify_schedule_problem(self, group: str, error_message: str):
        """
        Уведомление о проблеме с загрузкой расписания
        
        Args:
            group: Группа
            error_message: Сообщение об ошибке
        """
        if not self.is_enabled() or self.get_setting('notify_schedule_problems') != '1':
            return
        
        try:
            text = "📅 <b>ПРОБЛЕМА С РАСПИСАНИЕМ</b>\n\n"
            text += f"<b>Группа:</b> {group}\n"
            text += f"<b>Ошибка:</b> {error_message}\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            text += "Возможно, расписание не опубликовано на сайте или изменился формат."
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info(f"Schedule problem notification sent to admin: {group}")
            
        except Exception as e:
            logger.error(f"Failed to send schedule problem notification: {e}")
    
    async def notify_disk_space(self, used_percent: float, free_space: str):
        """
        Уведомление о заполнении диска
        
        Args:
            used_percent: Процент использования
            free_space: Свободное место
        """
        if not self.is_enabled() or self.get_setting('notify_disk_space') != '1':
            return
        
        # Уведомляем только если использовано больше 85%
        if used_percent < 85:
            return
        
        try:
            emoji = "⚠️" if used_percent < 95 else "🚨"
            
            text = f"{emoji} <b>ПРЕДУПРЕЖДЕНИЕ О МЕСТЕ НА ДИСКЕ</b>\n\n"
            text += f"<b>Использовано:</b> {used_percent:.1f}%\n"
            text += f"<b>Свободно:</b> {free_space}\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            
            if used_percent >= 95:
                text += "🚨 Критически мало места! Требуется срочная очистка."
            else:
                text += "Рекомендуется освободить место на диске."
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info("Disk space notification sent to admin")
            
        except Exception as e:
            logger.error(f"Failed to send disk space notification: {e}")
    
    async def notify_broadcast_completed(self, broadcast_id: int, success: int, errors: int):
        """
        Уведомление о завершении рассылки
        
        Args:
            broadcast_id: ID рассылки
            success: Успешно отправлено
            errors: Ошибок
        """
        if not self.is_enabled():
            return
        
        try:
            total = success + errors
            success_rate = (success / total * 100) if total > 0 else 0
            
            text = "📢 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
            text += f"<b>ID рассылки:</b> {broadcast_id}\n"
            text += f"<b>Всего:</b> {total}\n"
            text += f"<b>Успешно:</b> {success} ({success_rate:.1f}%)\n"
            text += f"<b>Ошибок:</b> {errors}\n"
            text += f"<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
            logger.info(f"Broadcast completion notification sent to admin: {broadcast_id}")
            
        except Exception as e:
            logger.error(f"Failed to send broadcast completion notification: {e}")
    
    async def notify_custom(self, message: str):
        """
        Отправить произвольное уведомление
        
        Args:
            message: Текст сообщения
        """
        if not self.is_enabled():
            return
        
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode="HTML")
            logger.info("Custom notification sent to admin")
            
        except Exception as e:
            logger.error(f"Failed to send custom notification: {e}")
    
    def get_settings_text(self) -> str:
        """
        Получить текст с текущими настройками
        
        Returns:
            Отформатированный текст
        """
        text = "🔔 <b>НАСТРОЙКИ УВЕДОМЛЕНИЙ АДМИНУ</b>\n\n"
        
        enabled = self.is_enabled()
        text += f"<b>Уведомления:</b> {'✅ Включены' if enabled else '❌ Выключены'}\n\n"
        
        if enabled:
            settings = {
                'notify_critical_errors': 'Критические ошибки',
                'notify_new_users': 'Новые пользователи',
                'notify_error_threshold': 'Превышение порога ошибок',
                'notify_schedule_problems': 'Проблемы с расписанием',
                'notify_disk_space': 'Заполнение диска'
            }
            
            for key, label in settings.items():
                value = self.get_setting(key)
                status = '✅' if value == '1' else '❌'
                text += f"{status} {label}\n"
            
            # Порог ошибок
            threshold_count = self.get_setting('error_threshold_count') or '10'
            threshold_minutes = self.get_setting('error_threshold_minutes') or '60'
            text += f"\n<b>Порог ошибок:</b> {threshold_count} за {threshold_minutes} мин\n"
        
        return text


# Глобальный экземпляр
_admin_notifications = None


def get_admin_notifications() -> AdminNotifications:
    """Получить глобальный экземпляр AdminNotifications"""
    global _admin_notifications
    if _admin_notifications is None:
        _admin_notifications = AdminNotifications()
    return _admin_notifications


# Вспомогательные функции для быстрого доступа
async def notify_admin_error(error_type: str, error_message: str, traceback: Optional[str] = None):
    """Быстрое уведомление об ошибке"""
    await get_admin_notifications().notify_critical_error(error_type, error_message, traceback)


async def notify_admin_new_user(user_id: int, username: Optional[str], group: str):
    """Быстрое уведомление о новом пользователе"""
    await get_admin_notifications().notify_new_user(user_id, username, group)


async def notify_admin_custom(message: str):
    """Быстрое произвольное уведомление"""
    await get_admin_notifications().notify_custom(message)
