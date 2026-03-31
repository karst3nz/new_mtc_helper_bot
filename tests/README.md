# Тесты для MTC Helper Bot

Этот каталог содержит pytest тесты для проекта MTC Helper Bot.

## Структура тестов

```
tests/
├── __init__.py           # Инициализация пакета тестов
├── conftest.py           # Общие фикстуры для всех тестов
├── test_db.py            # Тесты для utils/db.py
├── test_decorators.py    # Тесты для utils/decorators.py
├── test_menus.py         # Тесты для utils/menus.py
└── test_handlers.py      # Интеграционные тесты для handlers
```

## Установка зависимостей

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

## Запуск тестов

### Запустить все тесты:
```bash
pytest
```

### Запустить с подробным выводом:
```bash
pytest -v
```

### Запустить конкретный файл:
```bash
pytest tests/test_db.py
```

### Запустить конкретный тест:
```bash
pytest tests/test_db.py::TestDB::test_insert_user
```

### Запустить тесты по маркерам:
```bash
# Только unit тесты
pytest -m unit

# Только интеграционные тесты
pytest -m integration

# Только тесты базы данных
pytest -m db
```

### Запустить с покрытием кода:
```bash
pytest --cov=. --cov-report=html
```

## Маркеры тестов

- `@pytest.mark.unit` - Юнит-тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.db` - Тесты базы данных

## Фикстуры

### Основные фикстуры (conftest.py):

- `temp_db` - Временная база данных для тестов
- `mock_bot` - Мок объекта бота
- `mock_message` - Мок объекта сообщения
- `mock_callback_query` - Мок объекта callback query
- `mock_state` - Мок объекта FSMContext
- `mock_config` - Мок конфигурации
- `sample_user_data` - Примерные данные пользователя
- `sample_group_data` - Примерные данные группы

## Примеры использования

### Тестирование асинхронных функций:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value
```

### Использование моков:

```python
@patch('module.function')
async def test_with_mock(mock_function):
    mock_function.return_value = "mocked value"
    result = await function_under_test()
    assert result == "expected"
```

### Использование фикстур:

```python
def test_with_fixture(mock_message, mock_state):
    # Используем фикстуры в тесте
    assert mock_message.from_user.id == 12345
```

## Покрытие кода

После запуска тестов с флагом `--cov`, отчет о покрытии будет доступен в `htmlcov/index.html`.

## CI/CD

Тесты автоматически запускаются при каждом коммите через GitHub Actions (если настроено).

## Troubleshooting

### Проблема: ModuleNotFoundError
**Решение:** Убедитесь, что все зависимости установлены:
```bash
pip install -r requirements.txt
```

### Проблема: Тесты не находятся
**Решение:** Убедитесь, что вы запускаете pytest из корневой директории проекта.

### Проблема: Ошибки импорта
**Решение:** Добавьте корневую директорию в PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```
