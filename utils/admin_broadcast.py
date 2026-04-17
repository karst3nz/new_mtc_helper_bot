"""
Улучшенная система рассылок для администратора
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from aiogram import types
import aiogram.exceptions

from utils.db import DB
from utils.log import create_logger
from utils.admin_logger import get_admin_logger
from config import bot

logger = create_logger(__name__)


class BroadcastManager:
    """Менеджер рассылок"""
    
    def __init__(self):
        self.db = DB()
        self.admin_logger = get_admin_logger()
        self.active_broadcasts = {}  # {broadcast_id: {'cancel': bool}}
    
    def get_audience(self, filter_type: str, filter_params: Optional[Dict[str, Any]] = None) -> List[int]:
        """
        Получение списка user_id для рассылки по фильтрам
        
        Args:
            filter_type: Тип фильтра (all, by_group, by_activity, by_hours, test)
            filter_params: Параметры фильтра
        
        Returns:
            Список user_id
        """
        try:
            if filter_type == 'test':
                # Тестовая рассылка только админу
                from config import ADMIN_ID
                return [int(ADMIN_ID)]
            
            elif filter_type == 'all':
                # Все пользователи (не заблокированные)
                self.db.cursor.execute(
                    'SELECT user_id FROM users WHERE is_blocked = 0'
                )
                return [row[0] for row in self.db.cursor.fetchall()]
            
            elif filter_type == 'by_group':
                # По конкретным группам
                groups = filter_params.get('groups', [])
                if not groups:
                    return []
                
                placeholders = ','.join('?' * len(groups))
                query = f'''SELECT DISTINCT user_id FROM users 
                           WHERE (group_id IN ({placeholders}) OR sec_group_id IN ({placeholders}))
                           AND is_blocked = 0'''
                self.db.cursor.execute(query, groups + groups)
                return [row[0] for row in self.db.cursor.fetchall()]
            
            elif filter_type == 'by_activity':
                # По активности (активные за последние N дней)
                days = filter_params.get('days', 7)
                cutoff_date = datetime.now() - timedelta(days=days)
                
                self.db.cursor.execute(
                    '''SELECT user_id FROM users 
                       WHERE last_activity >= ? AND is_blocked = 0''',
                    (cutoff_date.isoformat(),)
                )
                return [row[0] for row in self.db.cursor.fetchall()]
            
            elif filter_type == 'by_hours':
                # По количеству пропущенных часов
                min_hours = filter_params.get('min_hours', 0)
                max_hours = filter_params.get('max_hours', 999999)
                
                self.db.cursor.execute(
                    '''SELECT user_id FROM users 
                       WHERE missed_hours >= ? AND missed_hours <= ? AND is_blocked = 0''',
                    (min_hours, max_hours)
                )
                return [row[0] for row in self.db.cursor.fetchall()]
            
            else:
                logger.warning(f"Unknown filter type: {filter_type}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get audience: {e}")
            return []
    
    def create_broadcast(self, admin_id: int, message_text: str, 
                        filter_type: str, filter_params: Optional[Dict[str, Any]] = None) -> int:
        """
        Создание новой рассылки
        
        Args:
            admin_id: ID администратора
            message_text: Текст сообщения
            filter_type: Тип фильтра
            filter_params: Параметры фильтра
        
        Returns:
            ID созданной рассылки
        """
        try:
            audience = self.get_audience(filter_type, filter_params)
            total_users = len(audience)
            
            filter_params_json = json.dumps(filter_params, ensure_ascii=False) if filter_params else None
            
            self.db.cursor.execute(
                '''INSERT INTO broadcasts 
                   (admin_id, message_text, filter_type, filter_params, total_users, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)''',
                (admin_id, message_text, filter_type, filter_params_json, total_users, datetime.now().isoformat())
            )
            self.db.conn.commit()
            
            broadcast_id = self.db.cursor.lastrowid
            
            # Логируем создание рассылки
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='broadcast_create',
                target_id=broadcast_id,
                details={
                    'filter_type': filter_type,
                    'total_users': total_users
                }
            )
            
            logger.info(f"Broadcast {broadcast_id} created by admin {admin_id}, audience: {total_users}")
            return broadcast_id
            
        except Exception as e:
            logger.error(f"Failed to create broadcast: {e}")
            return 0
    
    async def send_broadcast(self, broadcast_id: int, progress_callback=None) -> Dict[str, int]:
        """
        Отправка рассылки
        
        Args:
            broadcast_id: ID рассылки
            progress_callback: Callback для обновления прогресса
        
        Returns:
            Статистика отправки {success: int, errors: int}
        """
        try:
            # Получаем данные рассылки
            self.db.cursor.execute(
                '''SELECT admin_id, message_text, filter_type, filter_params, total_users
                   FROM broadcasts WHERE id = ?''',
                (broadcast_id,)
            )
            row = self.db.cursor.fetchone()
            
            if not row:
                logger.error(f"Broadcast {broadcast_id} not found")
                return {'success': 0, 'errors': 0}
            
            admin_id, message_text, filter_type, filter_params_json, total_users = row
            filter_params = json.loads(filter_params_json) if filter_params_json else None
            
            # Получаем аудиторию
            audience = self.get_audience(filter_type, filter_params)
            
            # Обновляем статус
            self.db.cursor.execute(
                'UPDATE broadcasts SET status = "in_progress" WHERE id = ?',
                (broadcast_id,)
            )
            self.db.conn.commit()
            
            # Инициализируем флаг отмены
            self.active_broadcasts[broadcast_id] = {'cancel': False}
            
            # Отправляем сообщения
            success_count = 0
            error_count = 0
            
            for i, user_id in enumerate(audience):
                # Проверяем флаг отмены
                if self.active_broadcasts[broadcast_id]['cancel']:
                    logger.info(f"Broadcast {broadcast_id} cancelled")
                    break
                
                # Отправляем сообщение
                result = await self._send_message(user_id, message_text)
                
                if result:
                    success_count += 1
                else:
                    error_count += 1
                
                # Обновляем прогресс каждые 5 сообщений
                if (i + 1) % 5 == 0 or (i + 1) == len(audience):
                    self.db.cursor.execute(
                        '''UPDATE broadcasts 
                           SET success_count = ?, error_count = ?
                           WHERE id = ?''',
                        (success_count, error_count, broadcast_id)
                    )
                    self.db.conn.commit()
                    
                    # Вызываем callback для обновления UI
                    if progress_callback:
                        await progress_callback(i + 1, len(audience), success_count, error_count)
                
                # Небольшая задержка для избежания flood limits
                await asyncio.sleep(0.05)
            
            # Обновляем финальный статус
            status = 'cancelled' if self.active_broadcasts[broadcast_id]['cancel'] else 'completed'
            self.db.cursor.execute(
                '''UPDATE broadcasts 
                   SET status = ?, success_count = ?, error_count = ?, completed_at = ?
                   WHERE id = ?''',
                (status, success_count, error_count, datetime.now().isoformat(), broadcast_id)
            )
            self.db.conn.commit()
            
            # Удаляем из активных
            del self.active_broadcasts[broadcast_id]
            
            # Логируем завершение
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='broadcast_complete',
                target_id=broadcast_id,
                details={
                    'success': success_count,
                    'errors': error_count,
                    'status': status
                }
            )
            
            logger.info(f"Broadcast {broadcast_id} completed: {success_count} success, {error_count} errors")
            
            return {'success': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Failed to send broadcast: {e}")
            return {'success': 0, 'errors': 0}
    
    async def _send_message(self, user_id: int, message_text: str, max_retries: int = 3) -> bool:
        """
        Отправка сообщения одному пользователю с обработкой ошибок
        
        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            max_retries: Максимальное количество попыток
        
        Returns:
            True если успешно, False если ошибка
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                return True
                
            except aiogram.exceptions.TelegramBadRequest as e:
                # Неисправимая ошибка (пользователь заблокировал бота, чат не найден и т.д.)
                logger.debug(f"BadRequest for user {user_id}: {e}")
                return False
                
            except aiogram.exceptions.TelegramRetryAfter as e:
                # Flood control - ждем и повторяем
                delay = getattr(e, "retry_after", None)
                if delay is None:
                    m = re.search(r"Retry in (\d+) seconds", str(e))
                    delay = int(m.group(1)) if m else 30
                
                logger.warning(f"Flood control for user {user_id}: waiting {delay}s")
                await asyncio.sleep(delay)
                retry_count += 1
                
            except Exception as e:
                # Другие ошибки
                logger.error(f"Error sending to user {user_id}: {e}")
                retry_count += 1
                await asyncio.sleep(1)
        
        return False
    
    def cancel_broadcast(self, broadcast_id: int, admin_id: int) -> bool:
        """
        Отмена активной рассылки
        
        Args:
            broadcast_id: ID рассылки
            admin_id: ID администратора
        
        Returns:
            True если успешно
        """
        try:
            if broadcast_id in self.active_broadcasts:
                self.active_broadcasts[broadcast_id]['cancel'] = True
                
                # Логируем отмену
                self.admin_logger.log_action(
                    admin_id=admin_id,
                    action='broadcast_cancel',
                    target_id=broadcast_id
                )
                
                logger.info(f"Broadcast {broadcast_id} cancellation requested by admin {admin_id}")
                return True
            else:
                logger.warning(f"Broadcast {broadcast_id} is not active")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel broadcast: {e}")
            return False
    
    def get_broadcast_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение истории рассылок
        
        Args:
            limit: Максимальное количество записей
        
        Returns:
            Список рассылок
        """
        try:
            self.db.cursor.execute(
                '''SELECT id, admin_id, message_text, filter_type, total_users, 
                          success_count, error_count, status, created_at, completed_at
                   FROM broadcasts
                   ORDER BY created_at DESC
                   LIMIT ?''',
                (limit,)
            )
            
            broadcasts = []
            for row in self.db.cursor.fetchall():
                broadcast = {
                    'id': row[0],
                    'admin_id': row[1],
                    'message_text': row[2],
                    'filter_type': row[3],
                    'total_users': row[4],
                    'success_count': row[5],
                    'error_count': row[6],
                    'status': row[7],
                    'created_at': row[8],
                    'completed_at': row[9]
                }
                broadcasts.append(broadcast)
            
            return broadcasts
            
        except Exception as e:
            logger.error(f"Failed to get broadcast history: {e}")
            return []
    
    def get_broadcast_stats(self, broadcast_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение статистики конкретной рассылки
        
        Args:
            broadcast_id: ID рассылки
        
        Returns:
            Статистика рассылки
        """
        try:
            self.db.cursor.execute(
                '''SELECT total_users, success_count, error_count, status, created_at, completed_at
                   FROM broadcasts WHERE id = ?''',
                (broadcast_id,)
            )
            
            row = self.db.cursor.fetchone()
            if not row:
                return None
            
            stats = {
                'total_users': row[0],
                'success_count': row[1],
                'error_count': row[2],
                'status': row[3],
                'created_at': row[4],
                'completed_at': row[5]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get broadcast stats: {e}")
            return None
    
    def format_broadcast_preview(self, filter_type: str, filter_params: Optional[Dict[str, Any]], 
                                 message_text: str) -> str:
        """
        Форматирование предпросмотра рассылки
        
        Args:
            filter_type: Тип фильтра
            filter_params: Параметры фильтра
            message_text: Текст сообщения
        
        Returns:
            Отформатированная строка
        """
        audience = self.get_audience(filter_type, filter_params)
        total_users = len(audience)
        
        filter_names = {
            'all': '👥 Всем пользователям',
            'by_group': '📚 По группам',
            'by_activity': '⚡ По активности',
            'by_hours': '⏰ По пропускам',
            'test': '🧪 Тестовая рассылка'
        }
        
        text = "📊 <b>Предпросмотр рассылки</b>\n\n"
        text += f"<b>Фильтр:</b> {filter_names.get(filter_type, filter_type)}\n"
        
        if filter_params:
            if 'groups' in filter_params:
                text += f"<b>Группы:</b> {', '.join(map(str, filter_params['groups']))}\n"
            if 'days' in filter_params:
                text += f"<b>Активность:</b> за последние {filter_params['days']} дней\n"
            if 'min_hours' in filter_params or 'max_hours' in filter_params:
                min_h = filter_params.get('min_hours', 0)
                max_h = filter_params.get('max_hours', 999999)
                text += f"<b>Пропуски:</b> от {min_h} до {max_h} часов\n"
        
        text += f"\n<b>Получателей:</b> {total_users}\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"{message_text}\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        
        return text
    
    def format_broadcast_history(self, broadcasts: List[Dict[str, Any]]) -> str:
        """
        Форматирование истории рассылок
        
        Args:
            broadcasts: Список рассылок
        
        Returns:
            Отформатированная строка
        """
        if not broadcasts:
            return "📜 История рассылок пуста"
        
        text = "📜 <b>История рассылок</b>\n\n"
        
        status_emoji = {
            'pending': '⏳',
            'in_progress': '📤',
            'completed': '✅',
            'cancelled': '🚫'
        }
        
        for broadcast in broadcasts:
            created = datetime.fromisoformat(broadcast['created_at']).strftime('%d.%m.%Y %H:%M')
            status = status_emoji.get(broadcast['status'], '❓')
            
            text += f"{status} <b>ID {broadcast['id']}</b> | {created}\n"
            text += f"Получателей: {broadcast['total_users']}\n"
            
            if broadcast['status'] in ['completed', 'cancelled']:
                text += f"✅ Успешно: {broadcast['success_count']} | "
                text += f"❌ Ошибок: {broadcast['error_count']}\n"
            
            # Показываем первые 50 символов сообщения
            preview = broadcast['message_text'][:50]
            if len(broadcast['message_text']) > 50:
                preview += "..."
            text += f"Текст: {preview}\n\n"
        
        return text


# Глобальный экземпляр
_broadcast_manager = None


def get_broadcast_manager() -> BroadcastManager:
    """Получить глобальный экземпляр BroadcastManager"""
    global _broadcast_manager
    if _broadcast_manager is None:
        _broadcast_manager = BroadcastManager()
    return _broadcast_manager
