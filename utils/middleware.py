"""
Middleware для проверки режима обслуживания и логирования активности
"""
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, InlineQuery
from utils.maintenance_mode import check_maintenance_access, get_maintenance_mode
from utils.log import create_logger

logger = create_logger(__name__)


class MaintenanceMiddleware(BaseMiddleware):
    """Middleware для проверки режима обслуживания"""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверяет режим обслуживания перед обработкой события
        
        Args:
            handler: Следующий обработчик
            event: Событие (Message, CallbackQuery и т.д.)
            data: Данные контекста
        
        Returns:
            Результат обработки
        """
        from utils.db import DB
        
        # Получаем user_id из события
        user_id = None
        
        if event.message:
            user_id = event.message.from_user.id
            event_obj = event.message
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            event_obj = event.callback_query
        elif event.inline_query:
            user_id = event.inline_query.from_user.id
            event_obj = event.inline_query
        else:
            # Для других типов событий пропускаем проверку
            return await handler(event, data)
        
        # Проверяем, заблокирован ли пользователь
        try:
            db = DB()
            db.cursor.execute('SELECT is_blocked FROM users WHERE user_id = ?', (user_id,))
            row = db.cursor.fetchone()
            
            if row and row[0] == 1:
                logger.info(f"Blocked user {user_id} tried to interact with bot")
                
                # Отправляем сообщение о блокировке
                if isinstance(event_obj, Message):
                    await event_obj.answer(
                        "🚫 <b>Доступ заблокирован</b>\n\n"
                        "Ваш аккаунт был заблокирован администратором.\n"
                        "Для получения дополнительной информации обратитесь к администратору.",
                        parse_mode="HTML"
                    )
                elif isinstance(event_obj, CallbackQuery):
                    await event_obj.answer(
                        "🚫 Ваш аккаунт заблокирован",
                        show_alert=True
                    )
                
                # Блокируем обработку
                return
        except Exception as e:
            logger.error(f"Error checking user block status: {e}")
        
        # Проверяем доступ в режиме обслуживания
        if not check_maintenance_access(user_id):
            maintenance = get_maintenance_mode()
            message_text = maintenance.get_maintenance_message()
            
            logger.info(f"Maintenance mode: blocked access for user {user_id}")
            
            # Отправляем сообщение о режиме обслуживания
            if isinstance(event_obj, Message):
                await event_obj.answer(message_text, parse_mode="HTML")
            elif isinstance(event_obj, CallbackQuery):
                await event_obj.answer(
                    "🔧 Бот находится на техническом обслуживании",
                    show_alert=True
                )
            
            # Не вызываем handler, блокируем обработку
            return
        
        # Если доступ разрешен, продолжаем обработку
        return await handler(event, data)


class UserActivityMiddleware(BaseMiddleware):
    """Middleware для логирования активности пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Логирует активность пользователей
        
        Args:
            handler: Следующий обработчик
            event: Событие
            data: Данные контекста
        
        Returns:
            Результат обработки
        """
        from utils.db import DB
        
        user_id = None
        action = None
        details = None
        
        # Определяем тип события и извлекаем данные
        if event.message:
            user_id = event.message.from_user.id
            
            # Определяем тип действия
            if event.message.text:
                if event.message.text.startswith('/'):
                    action = f"command:{event.message.text.split()[0]}"
                else:
                    action = "message"
                details = event.message.text[:100]  # Первые 100 символов
            elif event.message.photo:
                action = "photo"
            elif event.message.document:
                action = "document"
            else:
                action = "message"
        
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            action = "callback"
            details = event.callback_query.data[:100]  # Первые 100 символов
        
        elif event.inline_query:
            user_id = event.inline_query.from_user.id
            action = "inline_query"
            details = event.inline_query.query[:100]
        
        # Логируем активность
        if user_id and action:
            try:
                db = DB()
                
                # Записываем в user_activity
                db.cursor.execute(
                    '''INSERT INTO user_activity (user_id, action, details, timestamp)
                       VALUES (?, ?, ?, ?)''',
                    (user_id, action, details, datetime.now().isoformat())
                )
                
                # Обновляем last_activity в users
                db.cursor.execute(
                    '''UPDATE users SET last_activity = ? WHERE user_id = ?''',
                    (datetime.now().isoformat(), user_id)
                )
                
                db.conn.commit()
                
            except Exception as e:
                logger.error(f"Failed to log user activity: {e}")
        
        # Продолжаем обработку
        return await handler(event, data)
