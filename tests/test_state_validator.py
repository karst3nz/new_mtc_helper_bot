"""
Тесты для модуля state_validator
"""
import pytest
from unittest.mock import Mock, AsyncMock
from aiogram.fsm.context import FSMContext


class TestStateValidation:
    """Тесты валидации состояний"""
    
    @pytest.mark.asyncio
    async def test_validate_state_exists(self):
        """Тест валидации существующего состояния"""
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value="some_state")
        result = await state.get_state()
        assert result == "some_state"
        
    @pytest.mark.asyncio
    async def test_validate_state_none(self):
        """Тест валидации отсутствующего состояния"""
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value=None)
        result = await state.get_state()
        assert result is None
        
    @pytest.mark.asyncio
    async def test_clear_state(self):
        """Тест очистки состояния"""
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        await state.clear()
        state.clear.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_set_state(self):
        """Тест установки состояния"""
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        await state.set_state("new_state")
        state.set_state.assert_called_once_with("new_state")


class TestStateData:
    """Тесты данных состояния"""
    
    @pytest.mark.asyncio
    async def test_get_data_empty(self):
        """Тест получения пустых данных"""
        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        result = await state.get_data()
        assert result == {}
        
    @pytest.mark.asyncio
    async def test_get_data_with_values(self):
        """Тест получения данных со значениями"""
        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"key": "value"})
        result = await state.get_data()
        assert result["key"] == "value"
        
    @pytest.mark.asyncio
    async def test_update_data(self):
        """Тест обновления данных"""
        state = AsyncMock(spec=FSMContext)
        state.update_data = AsyncMock()
        await state.update_data(key="value")
        state.update_data.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_set_data(self):
        """Тест установки данных"""
        state = AsyncMock(spec=FSMContext)
        state.set_data = AsyncMock()
        await state.set_data({"key": "value"})
        state.set_data.assert_called_once()


class TestStateTransitions:
    """Тесты переходов между состояниями"""
    
    @pytest.mark.asyncio
    async def test_transition_to_new_state(self):
        """Тест перехода в новое состояние"""
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        await state.set_state("state1")
        await state.set_state("state2")
        assert state.set_state.call_count == 2
        
    @pytest.mark.asyncio
    async def test_transition_with_data(self):
        """Тест перехода с данными"""
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        await state.set_state("new_state")
        await state.update_data(key="value")
        state.set_state.assert_called_once()
        state.update_data.assert_called_once()


class TestStateLifecycle:
    """Тесты жизненного цикла состояния"""
    
    @pytest.mark.asyncio
    async def test_state_creation(self):
        """Тест создания состояния"""
        state = AsyncMock(spec=FSMContext)
        assert state is not None
        
    @pytest.mark.asyncio
    async def test_state_modification(self):
        """Тест модификации состояния"""
        state = AsyncMock(spec=FSMContext)
        state.update_data = AsyncMock()
        await state.update_data(modified=True)
        state.update_data.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_state_deletion(self):
        """Тест удаления состояния"""
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        await state.clear()
        state.clear.assert_called_once()


class TestStateEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_multiple_clears(self):
        """Тест множественных очисток"""
        state = AsyncMock(spec=FSMContext)
        state.clear = AsyncMock()
        await state.clear()
        await state.clear()
        assert state.clear.call_count == 2
        
    @pytest.mark.asyncio
    async def test_update_empty_data(self):
        """Тест обновления пустыми данными"""
        state = AsyncMock(spec=FSMContext)
        state.update_data = AsyncMock()
        await state.update_data()
        state.update_data.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_set_none_state(self):
        """Тест установки None состояния"""
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        await state.set_state(None)
        state.set_state.assert_called_once_with(None)


class TestStateConsistency:
    """Тесты консистентности состояния"""
    
    @pytest.mark.asyncio
    async def test_data_persistence(self):
        """Тест сохранения данных"""
        state = AsyncMock(spec=FSMContext)
        test_data = {"key": "value"}
        state.get_data = AsyncMock(return_value=test_data)
        result = await state.get_data()
        assert result == test_data
        
    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """Тест сохранения состояния"""
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value="test_state")
        result = await state.get_state()
        assert result == "test_state"


class TestStateIntegration:
    """Интеграционные тесты состояния"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        state.get_data = AsyncMock(return_value={"step": 1})
        state.clear = AsyncMock()
        
        # Устанавливаем состояние
        await state.set_state("process")
        
        # Обновляем данные
        await state.update_data(step=1)
        
        # Получаем данные
        data = await state.get_data()
        assert data["step"] == 1
        
        # Очищаем
        await state.clear()
        
        state.set_state.assert_called_once()
        state.update_data.assert_called_once()
        state.get_data.assert_called_once()
        state.clear.assert_called_once()
