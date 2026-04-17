"""
Система логирования действий администратора
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from utils.db import DB
from utils.log import create_logger

logger = create_logger(__name__)


class AdminLogger:
    """Класс для логирования действий администратора"""
    
    def __init__(self):
        self.db = DB()
    
    def log_action(self, admin_id: int, action: str, target_id: Optional[int] = None, 
                   details: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование действия администратора
        
        Args:
            admin_id: ID администратора
            action: Тип действия (broadcast, user_edit, user_delete, etc)
            target_id: ID цели действия (user_id, broadcast_id)
            details: Дополнительные детали в виде словаря
        """
        try:
            details_json = json.dumps(details, ensure_ascii=False) if details else None
            
            self.db.cursor.execute(
                '''INSERT INTO admin_logs (admin_id, action, target_id, details, timestamp)
                   VALUES (?, ?, ?, ?, ?)''',
                (admin_id, action, target_id, details_json, datetime.now().isoformat())
            )
            self.db.conn.commit()
            
            logger.info(f"Admin action logged: {action} by {admin_id}")
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
    
    def get_logs(self, limit: int = 50, action_filter: Optional[str] = None,
                 admin_id: Optional[int] = None, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получение логов действий администратора
        
        Args:
            limit: Максимальное количество записей
            action_filter: Фильтр по типу действия
            admin_id: Фильтр по ID администратора
            days: Количество дней для выборки
        
        Returns:
            Список логов
        """
        try:
            query = '''SELECT id, admin_id, action, target_id, details, timestamp
                       FROM admin_logs
                       WHERE timestamp >= ?'''
            params = [datetime.now() - timedelta(days=days)]
            
            if action_filter:
                query += ' AND action = ?'
                params.append(action_filter)
            
            if admin_id:
                query += ' AND admin_id = ?'
                params.append(admin_id)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            self.db.cursor.execute(query, params)
            rows = self.db.cursor.fetchall()
            
            logs = []
            for row in rows:
                log_entry = {
                    'id': row[0],
                    'admin_id': row[1],
                    'action': row[2],
                    'target_id': row[3],
                    'details': json.loads(row[4]) if row[4] else None,
                    'timestamp': row[5]
                }
                logs.append(log_entry)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get admin logs: {e}")
            return []
    
    def get_action_stats(self, days: int = 7) -> Dict[str, int]:
        """
        Получение статистики по типам действий
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Словарь {action: count}
        """
        try:
            self.db.cursor.execute(
                '''SELECT action, COUNT(*) as count
                   FROM admin_logs
                   WHERE timestamp >= ?
                   GROUP BY action
                   ORDER BY count DESC''',
                (datetime.now() - timedelta(days=days),)
            )
            
            stats = {}
            for row in self.db.cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get action stats: {e}")
            return {}
    
    def format_logs_for_display(self, logs: List[Dict[str, Any]]) -> str:
        """
        Форматирование логов для отображения в Telegram
        
        Args:
            logs: Список логов
        
        Returns:
            Отформатированная строка
        """
        if not logs:
            return "📋 Нет записей в журнале"
        
        action_names = {
            'broadcast': '📢 Рассылка',
            'broadcast_cancel': '🚫 Отмена рассылки',
            'user_block': '🚫 Блокировка пользователя',
            'user_unblock': '✅ Разблокировка пользователя',
            'user_delete': '🗑️ Удаление пользователя',
            'user_edit': '✏️ Изменение пользователя',
            'user_message': '✉️ Сообщение пользователю',
            'users_cleanup': '🗑️ Очистка пользователей',
            'users_export': '📥 Экспорт пользователей',
            'settings_change': '⚙️ Изменение настроек',
            'maintenance_on': '🔧 Включен режим обслуживания',
            'maintenance_off': '✅ Выключен режим обслуживания',
            'scheduler_restart': '🔄 Перезапуск планировщика',
            'cache_clear': '🗑️ Очистка кэша',
            'schedules_update': '📥 Обновление расписаний',
        }
        
        text = "📋 <b>Журнал действий администратора</b>\n\n"
        
        for log in logs:
            action_name = action_names.get(log['action'], log['action'])
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%d.%m.%Y %H:%M:%S')
            
            text += f"🕐 {timestamp}\n"
            text += f"{action_name}\n"
            
            if log['target_id']:
                text += f"ID цели: {log['target_id']}\n"
            
            if log['details']:
                # Показываем только важные детали
                if 'total_users' in log['details']:
                    text += f"Пользователей: {log['details']['total_users']}\n"
                if 'success' in log['details']:
                    text += f"Успешно: {log['details']['success']}\n"
                if 'errors' in log['details']:
                    text += f"Ошибок: {log['details']['errors']}\n"
                if 'reason' in log['details']:
                    text += f"Причина: {log['details']['reason']}\n"
            
            text += "\n"
        
        return text
    
    def export_logs(self, start_date: datetime, end_date: datetime) -> str:
        """
        Экспорт логов за период в текстовый формат
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
        
        Returns:
            Путь к файлу с логами
        """
        try:
            self.db.cursor.execute(
                '''SELECT admin_id, action, target_id, details, timestamp
                   FROM admin_logs
                   WHERE timestamp BETWEEN ? AND ?
                   ORDER BY timestamp DESC''',
                (start_date.isoformat(), end_date.isoformat())
            )
            
            rows = self.db.cursor.fetchall()
            
            filename = f"admin_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.txt"
            filepath = f"data/{filename}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Журнал действий администратора\n")
                f.write(f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n")
                f.write(f"Всего записей: {len(rows)}\n")
                f.write("=" * 80 + "\n\n")
                
                for row in rows:
                    f.write(f"Время: {row[4]}\n")
                    f.write(f"Администратор: {row[0]}\n")
                    f.write(f"Действие: {row[1]}\n")
                    if row[2]:
                        f.write(f"ID цели: {row[2]}\n")
                    if row[3]:
                        f.write(f"Детали: {row[3]}\n")
                    f.write("-" * 80 + "\n\n")
            
            logger.info(f"Admin logs exported to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export admin logs: {e}")
            return ""


class ErrorLogger:
    """Класс для логирования системных ошибок"""
    
    def __init__(self):
        self.db = DB()
    
    def log_error(self, error_type: str, error_message: str, 
                  traceback: Optional[str] = None, user_id: Optional[int] = None) -> None:
        """
        Логирование системной ошибки
        
        Args:
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
            traceback: Traceback ошибки
            user_id: ID пользователя (если применимо)
        """
        try:
            self.db.cursor.execute(
                '''INSERT INTO system_errors (error_type, error_message, traceback, user_id, timestamp)
                   VALUES (?, ?, ?, ?, ?)''',
                (error_type, error_message, traceback, user_id, datetime.now().isoformat())
            )
            self.db.conn.commit()
            
            logger.error(f"System error logged: {error_type} - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to log system error: {e}")
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение последних ошибок
        
        Args:
            limit: Максимальное количество записей
        
        Returns:
            Список ошибок
        """
        try:
            self.db.cursor.execute(
                '''SELECT id, error_type, error_message, traceback, user_id, timestamp
                   FROM system_errors
                   ORDER BY timestamp DESC
                   LIMIT ?''',
                (limit,)
            )
            
            errors = []
            for row in self.db.cursor.fetchall():
                error_entry = {
                    'id': row[0],
                    'error_type': row[1],
                    'error_message': row[2],
                    'traceback': row[3],
                    'user_id': row[4],
                    'timestamp': row[5]
                }
                errors.append(error_entry)
            
            return errors
            
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
    
    def get_error_stats(self, days: int = 1) -> Dict[str, int]:
        """
        Получение статистики ошибок по типам
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Словарь {error_type: count}
        """
        try:
            self.db.cursor.execute(
                '''SELECT error_type, COUNT(*) as count
                   FROM system_errors
                   WHERE timestamp >= ?
                   GROUP BY error_type
                   ORDER BY count DESC''',
                (datetime.now() - timedelta(days=days),)
            )
            
            stats = {}
            for row in self.db.cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {}
    
    def get_error_frequency(self, hours: int = 24) -> int:
        """
        Получение частоты ошибок за период
        
        Args:
            hours: Количество часов для анализа
        
        Returns:
            Количество ошибок
        """
        try:
            self.db.cursor.execute(
                '''SELECT COUNT(*) FROM system_errors
                   WHERE timestamp >= ?''',
                (datetime.now() - timedelta(hours=hours),)
            )
            
            count = self.db.cursor.fetchone()[0]
            return count
            
        except Exception as e:
            logger.error(f"Failed to get error frequency: {e}")
            return 0
    
    def format_errors_for_display(self, errors: List[Dict[str, Any]]) -> str:
        """
        Форматирование ошибок для отображения
        
        Args:
            errors: Список ошибок
        
        Returns:
            Отформатированная строка
        """
        if not errors:
            return "✅ Нет ошибок"
        
        text = "⚠️ <b>Последние ошибки</b>\n\n"
        
        for error in errors:
            timestamp = datetime.fromisoformat(error['timestamp']).strftime('%d.%m.%Y %H:%M:%S')
            
            text += f"🕐 {timestamp}\n"
            text += f"<b>Тип:</b> {error['error_type']}\n"
            text += f"<b>Сообщение:</b> {error['error_message'][:100]}\n"
            
            if error['user_id']:
                text += f"<b>User ID:</b> {error['user_id']}\n"
            
            text += "\n"
        
        return text


# Глобальные экземпляры
_admin_logger = None
_error_logger = None


def get_admin_logger() -> AdminLogger:
    """Получить глобальный экземпляр AdminLogger"""
    global _admin_logger
    if _admin_logger is None:
        _admin_logger = AdminLogger()
    return _admin_logger


def get_error_logger() -> ErrorLogger:
    """Получить глобальный экземпляр ErrorLogger"""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger
