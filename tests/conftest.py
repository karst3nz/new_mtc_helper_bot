import pytest
import os
import tempfile
import sqlite3
from unittest.mock import Mock, AsyncMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext


@pytest.fixture
def temp_db():
    """Создает временную базу данных для тестов"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_db.db")
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(temp_dir)


@pytest.fixture
def mock_bot():
    """Мок объекта бота"""
    bot = AsyncMock()
    bot.id = 123456789
    bot.username = "test_bot"
    return bot


@pytest.fixture
def mock_message():
    """Мок объекта сообщения"""
    message = Mock(spec=types.Message)
    message.message_id = 1
    message.from_user = Mock()
    message.from_user.id = 12345
    message.from_user.username = "test_user"
    message.from_user.full_name = "Test User"
    message.chat = Mock()
    message.chat.id = 12345
    message.chat.type = "private"
    message.text = "test message"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query():
    """Мок объекта callback query"""
    callback = Mock(spec=types.CallbackQuery)
    callback.id = "test_callback_id"
    callback.from_user = Mock()
    callback.from_user.id = 12345
    callback.from_user.username = "test_user"
    callback.from_user.full_name = "Test User"
    callback.data = "test_data"
    callback.message = Mock()
    callback.message.chat = Mock()
    callback.message.chat.id = 12345
    callback.message.chat.type = "private"
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_state():
    """Мок объекта FSMContext"""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_config():
    """Мок конфигурации"""
    with patch('config.ADMIN_ID', '12345'), \
         patch('config.groups', ['3191', '3395', '3195']), \
         patch('config.db_DIR', 'database/'):
        yield


@pytest.fixture
def sample_user_data():
    """Примерные данные пользователя"""
    return {
        'user_id': 12345,
        'tg_username': 'test_user',
        'group_id': '3191',
        'sec_group_id': '3395',
        'missed_hours': 0,
        'show_missed_hours_mode': None,
        'smena': '1'
    }


@pytest.fixture
def sample_group_data():
    """Примерные данные группы"""
    return {
        'id': -100123456789,
        'user_id': 12345,
        'group': '3191',
        'pin_new_rasp': False
    }
