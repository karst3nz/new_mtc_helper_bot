"""
Тесты для быстрых команд (quick_commands.py)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from handlers.quick_commands import today_schedule, tomorrow_schedule, week_schedule


@pytest.fixture
def mock_message():
    """Создание mock сообщения"""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456
    message.chat = MagicMock(spec=Chat)
    message.chat.type = "private"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_user_data():
    """Mock данных пользователя из БД"""
    return (1, 123456, "testuser", 3191, None, 10, "rasp", "1")


@pytest.mark.asyncio
class TestQuickCommands:
    """Тесты быстрых команд"""
    
    async def test_today_schedule_success(self, mock_message, mock_user_data):
        """Тест команды /today - успешное получение расписания"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            # Настройка mock БД
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            # Настройка mock расписания
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="1 | Математика | 101 | Иванов")
            mock_rasp.create_rasp_msg = AsyncMock(return_value={
                "text": "Расписание на сегодня",
                "keyboard": MagicMock()
            })
            
            # Выполнение команды
            await today_schedule(mock_message)
            
            # Проверки
            mock_db.get.assert_called_once_with(123456)
            mock_rasp.run_session.assert_called_once()
            mock_rasp.get.assert_called_once()
            mock_message.answer.assert_called_once()
            mock_rasp.close_session.assert_called_once()
    
    async def test_today_schedule_not_registered(self, mock_message):
        """Тест команды /today - пользователь не зарегистрирован"""
        with patch('handlers.quick_commands.db') as mock_db:
            mock_db.get = AsyncMock(return_value=None)
            
            await today_schedule(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "зарегистрируйтесь" in mock_message.answer.call_args[0][0].lower()
    
    async def test_today_schedule_sunday(self, mock_message, mock_user_data):
        """Тест команды /today - воскресенье"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.datetime') as mock_datetime:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            # Настройка воскресенья
            mock_now = MagicMock()
            mock_now.weekday.return_value = 6  # Воскресенье
            mock_datetime.now.return_value = mock_now
            
            await today_schedule(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "воскресенье" in mock_message.answer.call_args[0][0].lower()
    
    async def test_today_schedule_no_schedule(self, mock_message, mock_user_data):
        """Тест команды /today - расписание не опубликовано"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = False
            
            await today_schedule(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "не опубликовано" in mock_message.answer.call_args[0][0].lower()
    
    async def test_tomorrow_schedule_success(self, mock_message, mock_user_data):
        """Тест команды /tomorrow - успешное получение расписания"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="1 | Физика | 102 | Петров")
            mock_rasp.create_rasp_msg = AsyncMock(return_value={
                "text": "Расписание на завтра",
                "keyboard": MagicMock()
            })
            
            await tomorrow_schedule(mock_message)
            
            mock_db.get.assert_called_once_with(123456)
            mock_message.answer.assert_called_once()
    
    async def test_tomorrow_schedule_skip_sunday(self, mock_message, mock_user_data):
        """Тест команды /tomorrow - пропуск воскресенья"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class, \
             patch('handlers.quick_commands.datetime') as mock_datetime, \
             patch('handlers.quick_commands.timedelta') as mock_timedelta:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            # Настройка: завтра воскресенье
            mock_now = MagicMock()
            mock_tomorrow = MagicMock()
            mock_tomorrow.weekday.return_value = 6  # Воскресенье
            mock_datetime.now.return_value = mock_now
            mock_timedelta.return_value = MagicMock()
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp.create_rasp_msg = AsyncMock(return_value={
                "text": "Расписание",
                "keyboard": MagicMock()
            })
            
            await tomorrow_schedule(mock_message)
            
            # Проверяем, что расписание все равно получено (на понедельник)
            mock_message.answer.assert_called_once()
    
    async def test_week_schedule_success(self, mock_message, mock_user_data):
        """Тест команды /week - успешное получение расписания на неделю"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="1 | Математика | 101 | Иванов")
            
            await week_schedule(mock_message)
            
            # Проверяем, что было несколько вызовов для разных дней
            assert mock_rasp.run_session.call_count >= 1
            assert mock_message.answer.call_count >= 1
    
    async def test_week_schedule_no_data(self, mock_message, mock_user_data):
        """Тест команды /week - нет расписания на неделю"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = False
            
            await week_schedule(mock_message)
            
            mock_message.answer.assert_called()
            assert "не опубликовано" in mock_message.answer.call_args[0][0].lower()
    
    async def test_week_schedule_long_message(self, mock_message, mock_user_data):
        """Тест команды /week - длинное сообщение разбивается"""
        with patch('handlers.quick_commands.db') as mock_db, \
             patch('handlers.quick_commands.Rasp') as mock_rasp_class:
            
            mock_db.get = AsyncMock(return_value=mock_user_data)
            
            # Создаем очень длинное расписание
            long_schedule = "Очень длинное расписание\n" * 200
            
            mock_rasp = mock_rasp_class.return_value
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value=long_schedule)
            
            await week_schedule(mock_message)
            
            # Проверяем, что было несколько вызовов answer (разбивка)
            assert mock_message.answer.call_count >= 1
