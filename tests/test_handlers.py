import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext


@pytest.mark.integration
class TestHandlers:
    """Интеграционные тесты для обработчиков"""
    
    @pytest.mark.asyncio
    @patch('handlers.cmd.menus')
    async def test_start_command(self, mock_menus):
        """Тест команды /start"""
        from handlers.cmd import start
        
        mock_menus.start = AsyncMock(return_value=("Test text", Mock()))
        
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 12345
        message.chat = Mock()
        message.chat.type = "private"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        
        await start(message, state)
        
        state.clear.assert_called_once()
        message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.cmd.menus')
    async def test_settings_command(self, mock_menus):
        """Тест команды /settings"""
        from handlers.cmd import settings
        
        mock_menus.settings = AsyncMock(return_value=("Settings text", Mock()))
        
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 12345
        message.chat = Mock()
        message.chat.type = "private"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        
        await settings(message, state)
        
        state.clear.assert_called_once()
        message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.cmd.menus')
    async def test_hours_command(self, mock_menus):
        """Тест команды /hours"""
        from handlers.cmd import hours
        
        mock_menus.add_missing_hours = AsyncMock(return_value=("Hours text", Mock()))
        
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 12345
        message.chat = Mock()
        message.chat.type = "private"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        
        await hours(message, state)
        
        state.clear.assert_called_once()
        message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.msg.DB')
    @patch('handlers.msg.start')
    @patch('config.groups', ['3191', '3395'])
    async def test_reg_group_handler(self, mock_start, mock_db_class):
        """Тест регистрации группы"""
        from handlers.msg import reg_group
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_start.return_value = ("Success", Mock())
        
        message = Mock(spec=types.Message)
        message.text = "3191"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        
        await reg_group(message, state)
        
        message.answer.assert_called_once()
        state.set_state.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.msg.DB')
    @patch('config.groups', ['3191', '3395'])
    async def test_change_main_group_handler(self, mock_db_class):
        """Тест изменения основной группы"""
        from handlers.msg import change_main_group
        
        mock_db = Mock()
        mock_db.update.return_value = True
        mock_db_class.return_value = mock_db
        
        message = Mock(spec=types.Message)
        message.text = "3395"
        message.from_user = Mock()
        message.from_user.id = 12345
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        
        await change_main_group(message, state)
        
        state.clear.assert_called_once()
        message.answer.assert_called_once()
        mock_db.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_msg_callback(self):
        """Тест удаления сообщения через callback"""
        from handlers.inline import delete_msg
        
        callback = Mock(spec=types.CallbackQuery)
        callback.message = Mock()
        callback.message.delete = AsyncMock()
        callback.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        
        await delete_msg(callback, state)
        
        state.clear.assert_called_once()
        callback.message.delete.assert_called_once()
        callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.inline.bot')
    async def test_check_pin_rights_success(self, mock_bot):
        """Тест проверки прав на закрепление - успех"""
        from handlers.inline import check_pin_rights
        
        callback = Mock(spec=types.CallbackQuery)
        callback.message = Mock()
        callback.message.pin = AsyncMock()
        callback.message.unpin = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        await check_pin_rights(callback)
        
        callback.message.pin.assert_called_once()
        callback.message.unpin.assert_called_once()
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('handlers.inline.bot')
    async def test_check_pin_rights_fail(self, mock_bot):
        """Тест проверки прав на закрепление - неудача"""
        from handlers.inline import check_pin_rights
        
        callback = Mock(spec=types.CallbackQuery)
        callback.message = Mock()
        callback.message.pin = AsyncMock(side_effect=Exception("No permission"))
        callback.message.reply = AsyncMock()
        callback.answer = AsyncMock()
        
        await check_pin_rights(callback)
        
        callback.message.reply.assert_called_once()
        callback.answer.assert_called_once()
