import pytest
import sqlite3
import os
from unittest.mock import patch, Mock, AsyncMock
from utils.db import DB


@pytest.mark.db
class TestDB:
    """Тесты для класса DB"""
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    def test_db_initialization(self, tmp_path):
        """Тест инициализации базы данных"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            assert db.conn is not None
            assert db.cursor is not None
            assert db.users_table == "users"
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    def test_create_tables(self, tmp_path):
        """Тест создания таблиц"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            
            # Проверяем, что таблица users создана
            db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert db.cursor.fetchone() is not None
            
            # Проверяем, что таблица groups создана
            db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
            assert db.cursor.fetchone() is not None
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    @patch('config.ADMIN_ID', '12345')
    @patch('asyncio.create_task')
    def test_insert_user(self, mock_create_task, tmp_path):
        """Тест вставки пользователя"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            
            user_id = 12345
            tg_username = "test_user"
            group_id = "3191"
            sec_group_id = "3395"
            
            db.insert(user_id, tg_username, group_id, sec_group_id)
            
            # Проверяем, что пользователь добавлен
            db.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            result = db.cursor.fetchone()
            assert result is not None
            assert result[1] == user_id  # user_id
            assert result[2] == tg_username  # tg_username
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    @patch('asyncio.create_task')
    def test_is_exists(self, mock_create_task, tmp_path):
        """Тест проверки существования пользователя"""
        with patch('config.db_DIR', str(tmp_path) + '/'), \
             patch('config.ADMIN_ID', '12345'):
            db = DB()
            
            user_id = 12345
            
            # Пользователь не существует
            assert db.is_exists(user_id) is False
            
            # Добавляем пользователя
            db.insert(user_id, "test_user", "3191", None)
            
            # Пользователь существует
            assert db.is_exists(user_id) is True
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    @patch('asyncio.create_task')
    def test_get_user_groups(self, mock_create_task, tmp_path):
        """Тест получения групп пользователя"""
        with patch('config.db_DIR', str(tmp_path) + '/'), \
             patch('config.ADMIN_ID', '12345'):
            db = DB()
            
            user_id = 12345
            group_id = "3191"
            sec_group_id = "3395"
            
            db.insert(user_id, "test_user", group_id, sec_group_id)
            
            # Получаем группы
            group, sec_group = db.get_user_groups(user_id)
            # БД возвращает int, поэтому сравниваем как строки
            assert str(group) == group_id
            assert str(sec_group) == sec_group_id
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    @patch('asyncio.create_task')
    def test_update_user(self, mock_create_task, tmp_path):
        """Тест обновления данных пользователя"""
        with patch('config.db_DIR', str(tmp_path) + '/'), \
             patch('config.ADMIN_ID', '12345'):
            db = DB()
            
            user_id = 12345
            db.insert(user_id, "test_user", "3191", None)
            
            # Обновляем группу
            new_group = "3395"
            result = db.update(user_id, "group_id", new_group, "users")
            assert result is True
            
            # Проверяем обновление
            group, _ = db.get_user_groups(user_id)
            assert str(group) == new_group
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    def test_insert_group(self, tmp_path):
        """Тест вставки группы"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            
            chat_id = -100123456789
            user_id = 12345
            group = "3191"
            
            db.insert_group(chat_id, user_id, group)
            
            # Проверяем, что группа добавлена
            db.cursor.execute("SELECT * FROM groups WHERE id = ?", (chat_id,))
            result = db.cursor.fetchone()
            assert result is not None
            assert result[0] == chat_id
            assert str(result[2]) == group  # Преобразуем к строке для сравнения
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    def test_is_group_exists(self, tmp_path):
        """Тест проверки существования группы"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            
            chat_id = -100123456789
            
            # Группа не существует
            assert db.is_group_exists(chat_id) is False
            
            # Добавляем группу
            db.insert_group(chat_id, 12345, "3191")
            
            # Группа существует
            assert db.is_group_exists(chat_id) is True
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    @patch('asyncio.create_task')
    def test_get_all(self, mock_create_task, tmp_path):
        """Тест получения всех значений колонки"""
        with patch('config.db_DIR', str(tmp_path) + '/'), \
             patch('config.ADMIN_ID', '12345'):
            db = DB()
            
            # Добавляем несколько пользователей
            db.insert(12345, "user1", "3191", None)
            db.insert(67890, "user2", "3395", None)
            
            # Получаем все user_id
            user_ids = db.get_all("user_id", "users")
            assert len(user_ids) == 2
            assert 12345 in user_ids
            assert 67890 in user_ids
    
    @patch('config.db_DIR', 'database/')
    @patch('config.bot', Mock())
    def test_validate_identifier(self, tmp_path):
        """Тест валидации идентификаторов"""
        with patch('config.db_DIR', str(tmp_path) + '/'):
            db = DB()
            
            # Валидная таблица
            assert db._validate_identifier("users", db.ALLOWED_TABLES, "table") == "users"
            
            # Невалидная таблица
            with pytest.raises(ValueError):
                db._validate_identifier("malicious_table", db.ALLOWED_TABLES, "table")
            
            # Валидная колонка
            assert db._validate_identifier("user_id", db.ALLOWED_COLUMNS, "column") == "user_id"
            
            # Невалидная колонка
            with pytest.raises(ValueError):
                db._validate_identifier("malicious_column", db.ALLOWED_COLUMNS, "column")
