"""
Примеры использования pytest для MTC Helper Bot

Этот файл содержит примеры различных паттернов тестирования,
используемых в проекте.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


# ============================================================================
# ПРИМЕР 1: Простой unit-тест
# ============================================================================

def test_simple_function():
    """Простой тест функции"""
    result = 2 + 2
    assert result == 4


# ============================================================================
# ПРИМЕР 2: Асинхронный тест
# ============================================================================

@pytest.mark.asyncio
async def test_async_function():
    """Тест асинхронной функции"""
    async def async_add(a, b):
        return a + b
    
    result = await async_add(2, 3)
    assert result == 5


# ============================================================================
# ПРИМЕР 3: Использование фикстур
# ============================================================================

@pytest.fixture
def sample_data():
    """Фикстура с тестовыми данными"""
    return {"user_id": 12345, "username": "test_user"}


def test_with_fixture(sample_data):
    """Тест с использованием фикстуры"""
    assert sample_data["user_id"] == 12345
    assert sample_data["username"] == "test_user"


# ============================================================================
# ПРИМЕР 4: Параметризованные тесты
# ============================================================================

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
])
def test_multiply_by_two(input, expected):
    """Параметризованный тест"""
    assert input * 2 == expected


# ============================================================================
# ПРИМЕР 5: Мокирование с patch
# ============================================================================

@patch('config.ADMIN_ID', '12345')
def test_with_patch():
    """Тест с использованием patch"""
    from config import ADMIN_ID
    assert ADMIN_ID == '12345'


# ============================================================================
# ПРИМЕР 6: Мокирование асинхронных функций
# ============================================================================

@pytest.mark.asyncio
async def test_async_mock():
    """Тест с AsyncMock"""
    mock_func = AsyncMock(return_value="mocked result")
    result = await mock_func()
    assert result == "mocked result"
    mock_func.assert_called_once()


# ============================================================================
# ПРИМЕР 7: Тестирование исключений
# ============================================================================

def test_exception():
    """Тест проверки исключений"""
    with pytest.raises(ValueError):
        raise ValueError("Test error")


def test_exception_message():
    """Тест проверки сообщения исключения"""
    with pytest.raises(ValueError, match="Test error"):
        raise ValueError("Test error")


# ============================================================================
# ПРИМЕР 8: Использование маркеров
# ============================================================================

@pytest.mark.unit
def test_marked_as_unit():
    """Тест помеченный как unit"""
    assert True


@pytest.mark.integration
def test_marked_as_integration():
    """Тест помеченный как integration"""
    assert True


@pytest.mark.slow
def test_marked_as_slow():
    """Тест помеченный как slow"""
    import time
    time.sleep(0.1)
    assert True


# ============================================================================
# ПРИМЕР 9: Мокирование объектов aiogram
# ============================================================================

@pytest.mark.asyncio
async def test_aiogram_message():
    """Тест с мокированием aiogram Message"""
    from aiogram import types
    
    message = Mock(spec=types.Message)
    message.text = "test"
    message.from_user = Mock()
    message.from_user.id = 12345
    message.answer = AsyncMock()
    
    await message.answer("Response")
    message.answer.assert_called_once_with("Response")


# ============================================================================
# ПРИМЕР 10: Тестирование базы данных
# ============================================================================

@pytest.mark.db
def test_database_operation(tmp_path):
    """Тест операций с базой данных"""
    import sqlite3
    
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'test')")
    conn.commit()
    
    cursor.execute("SELECT * FROM test")
    result = cursor.fetchone()
    
    assert result == (1, 'test')
    conn.close()


# ============================================================================
# ПРИМЕР 11: Использование множественных фикстур
# ============================================================================

@pytest.fixture
def user_id():
    return 12345


@pytest.fixture
def username():
    return "test_user"


def test_multiple_fixtures(user_id, username):
    """Тест с несколькими фикстурами"""
    assert user_id == 12345
    assert username == "test_user"


# ============================================================================
# ПРИМЕР 12: Setup и Teardown
# ============================================================================

@pytest.fixture
def setup_teardown():
    """Фикстура с setup и teardown"""
    # Setup
    print("\nSetup")
    data = {"initialized": True}
    
    yield data
    
    # Teardown
    print("\nTeardown")
    data.clear()


def test_with_setup_teardown(setup_teardown):
    """Тест с setup и teardown"""
    assert setup_teardown["initialized"] is True


# ============================================================================
# ПРИМЕР 13: Мокирование side_effect
# ============================================================================

@pytest.mark.asyncio
async def test_side_effect():
    """Тест с side_effect"""
    mock_func = AsyncMock(side_effect=[1, 2, 3])
    
    assert await mock_func() == 1
    assert await mock_func() == 2
    assert await mock_func() == 3


# ============================================================================
# ПРИМЕР 14: Проверка вызовов mock
# ============================================================================

def test_mock_calls():
    """Тест проверки вызовов mock"""
    mock = Mock()
    
    mock.method(1, 2, key="value")
    
    mock.method.assert_called_once()
    mock.method.assert_called_with(1, 2, key="value")
    assert mock.method.call_count == 1


# ============================================================================
# ПРИМЕР 15: Контекстный менеджер для patch
# ============================================================================

def test_patch_context_manager():
    """Тест с patch как контекстным менеджером"""
    with patch('config.ADMIN_ID', '99999'):
        from config import ADMIN_ID
        assert ADMIN_ID == '99999'


# ============================================================================
# ЗАПУСК ПРИМЕРОВ
# ============================================================================

if __name__ == "__main__":
    print("Запустите: pytest tests/test_examples.py -v")
