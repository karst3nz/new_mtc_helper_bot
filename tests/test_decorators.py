import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram import types
from utils.decorators import check_chat_type, check_group, if_admin


@pytest.mark.unit
class TestDecorators:
    """Тесты для декораторов"""
    
    @pytest.mark.asyncio
    async def test_check_chat_type_private_success(self):
        """Тест check_chat_type для приватного чата - успех"""
        @check_chat_type("private")
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.chat = Mock()
        message.chat.type = "private"
        message.answer = AsyncMock()
        
        result = await handler(message)
        assert result == "success"
        message.answer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_chat_type_private_fail(self):
        """Тест check_chat_type для приватного чата - неудача"""
        @check_chat_type("private")
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.chat = Mock()
        message.chat.type = "group"
        message.answer = AsyncMock()
        
        result = await handler(message)
        assert result is None
        message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_chat_type_group_success(self):
        """Тест check_chat_type для группового чата - успех"""
        @check_chat_type("group")
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.chat = Mock()
        message.chat.type = "group"
        message.answer = AsyncMock()
        
        result = await handler(message)
        assert result == "success"
        message.answer.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('config.groups', ['3191', '3395', '3195'])
    async def test_check_group_valid(self):
        """Тест check_group с валидной группой"""
        @check_group()
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.text = "3191"
        message.answer = AsyncMock()
        
        result = await handler(message)
        assert result == "success"
        message.answer.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('config.groups', ['3191', '3395', '3195'])
    async def test_check_group_invalid(self):
        """Тест check_group с невалидной группой"""
        @check_group()
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.text = "9999"
        message.answer = AsyncMock()
        
        result = await handler(message)
        assert result is None
        message.answer.assert_called_once()
        # Проверяем, что был вызван с текстом об ошибке
        call_args = message.answer.call_args
        assert call_args is not None
        assert "не знаю такую группу" in call_args[0][0] or "не знаю такую группу" in str(call_args)
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_msg_success(self):
        """Тест if_admin для сообщения - успех"""
        @if_admin("msg")
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 12345
        
        result = await handler(message)
        assert result == "success"
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_msg_fail(self):
        """Тест if_admin для сообщения - неудача"""
        @if_admin("msg")
        async def handler(message: types.Message):
            return "success"
        
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 67890
        
        result = await handler(message)
        assert result is None
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_call_success(self):
        """Тест if_admin для callback - успех"""
        @if_admin("call")
        async def handler(call: types.CallbackQuery):
            return "success"
        
        call = Mock(spec=types.CallbackQuery)
        call.from_user = Mock()
        call.from_user.id = 12345
        
        result = await handler(call)
        assert result == "success"
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_call_fail(self):
        """Тест if_admin для callback - неудача"""
        @if_admin("call")
        async def handler(call: types.CallbackQuery):
            return "success"
        
        call = Mock(spec=types.CallbackQuery)
        call.from_user = Mock()
        call.from_user.id = 67890
        
        result = await handler(call)
        assert result is None
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_user_id_success(self):
        """Тест if_admin для user_id - успех"""
        @if_admin("user_id")
        async def handler(user_id: int):
            return "success"
        
        result = await handler(12345)
        assert result == "success"
    
    @pytest.mark.asyncio
    @patch('utils.decorators.ADMIN_ID', '12345')
    async def test_if_admin_user_id_fail(self):
        """Тест if_admin для user_id - неудача"""
        @if_admin("user_id")
        async def handler(user_id: int):
            return "success"
        
        result = await handler(67890)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Тест сохранения метаданных функции декоратором"""
        @check_chat_type("private")
        async def test_handler(message: types.Message):
            """Test handler docstring"""
            pass
        
        assert test_handler.__name__ == "test_handler"
        assert test_handler.__doc__ == "Test handler docstring"
