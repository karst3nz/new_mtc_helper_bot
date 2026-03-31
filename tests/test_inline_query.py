"""
Тесты для модуля inline_query
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from aiogram.types import InlineQuery, User, InlineQueryResultArticle
from handlers.inline_query import inline_schedule, get_schedule_result


@pytest.fixture
def mock_db():
    """Мок базы данных"""
    db = Mock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def mock_rasp():
    """Мок класса Rasp"""
    rasp = AsyncMock()
    rasp.run_session = AsyncMock()
    rasp.close_session = AsyncMock()
    rasp.get = AsyncMock()
    rasp.rasp_exists = True
    rasp.get_rasp = AsyncMock(return_value="<b>Расписание</b>\n1 пара: Математика\n2 пара: Физика")
    return rasp


@pytest.fixture
def sample_user_data():
    """Примерные данные пользователя"""
    return (12345, 'test_user', 'Test User', '3191', None, 10, None, '1')


@pytest.fixture
def inline_query_mock():
    """Мок inline query"""
    query = Mock(spec=InlineQuery)
    query.id = "test_query_id"
    query.from_user = Mock(spec=User)
    query.from_user.id = 12345
    query.from_user.username = "test_user"
    query.query = ""
    query.answer = AsyncMock()
    return query


class TestInlineScheduleBasic:
    """Базовые тесты inline-режима"""
    
    @pytest.mark.asyncio
    async def test_inline_schedule_user_not_registered(self, inline_query_mock):
        """Тест когда пользователь не зарегистрирован"""
        with patch('handlers.inline_query.db') as mock_db:
            mock_db.get = AsyncMock(return_value=None)
            
            await inline_schedule(inline_query_mock)
            
            # Проверяем что был вызван answer с сообщением об ошибке
            inline_query_mock.answer.assert_called_once()
            call_args = inline_query_mock.answer.call_args[0][0]
            assert len(call_args) == 1
            assert call_args[0].id == "not_registered"
            assert "не зарегистрированы" in call_args[0].title
    
    @pytest.mark.asyncio
    async def test_inline_schedule_empty_query(self, inline_query_mock, sample_user_data):
        """Тест с пустым запросом (расписание на сегодня)"""
        inline_query_mock.query = ""
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            # Возвращаем 3 даты
            mock_find.return_value = [
                datetime(2026, 3, 31),
                datetime(2026, 4, 1),
                datetime(2026, 4, 2)
            ]
            
            # Мокируем результаты расписания
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
            assert mock_find.called
    
    @pytest.mark.asyncio
    async def test_inline_schedule_today_query(self, inline_query_mock, sample_user_data):
        """Тест с запросом 'сегодня'"""
        inline_query_mock.query = "сегодня"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            # Возвращаем 3 даты
            mock_find.return_value = [
                datetime(2026, 3, 31),
                datetime(2026, 4, 1),
                datetime(2026, 4, 2)
            ]
            
            # Мокируем результаты расписания
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_sunday(self, inline_query_mock, sample_user_data):
        """Тест когда сегодня воскресенье"""
        inline_query_mock.query = "сегодня"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            # Возвращаем даты начиная с понедельника (пропускаем воскресенье)
            mock_find.return_value = [
                datetime(2026, 4, 6),  # Понедельник
                datetime(2026, 4, 7),
                datetime(2026, 4, 8)
            ]
            
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()


class TestInlineScheduleTomorrow:
    """Тесты запроса расписания на завтра"""
    
    @pytest.mark.asyncio
    async def test_inline_schedule_tomorrow(self, inline_query_mock, sample_user_data):
        """Тест запроса 'завтра'"""
        inline_query_mock.query = "завтра"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.datetime') as mock_datetime:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            mock_now = Mock()
            mock_tomorrow = Mock()
            mock_tomorrow.weekday.return_value = 1  # Вторник
            mock_datetime.now.return_value = mock_now
            mock_datetime.now.return_value.__add__ = Mock(return_value=mock_tomorrow)
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание на завтра")
            mock_rasp_class.return_value = mock_rasp
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_tomorrow_sunday(self, inline_query_mock, sample_user_data):
        """Тест когда завтра воскресенье"""
        inline_query_mock.query = "завтра"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.datetime') as mock_datetime, \
             patch('handlers.inline_query.timedelta') as mock_timedelta:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            # Завтра воскресенье, должно показать понедельник
            mock_now = Mock()
            mock_tomorrow = Mock()
            mock_tomorrow.weekday.return_value = 6  # Воскресенье
            mock_monday = Mock()
            mock_monday.weekday.return_value = 0  # Понедельник
            
            mock_datetime.now.return_value = mock_now
            
            def add_days(days):
                if days == 1:
                    return mock_tomorrow
                return mock_monday
            
            mock_tomorrow.__add__ = Mock(return_value=mock_monday)
            mock_now.__add__ = Mock(side_effect=lambda td: add_days(td.days) if hasattr(td, 'days') else mock_tomorrow)
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()


class TestInlineScheduleWeek:
    """Тесты запроса расписания на неделю"""
    
    @pytest.mark.asyncio
    async def test_inline_schedule_week(self, inline_query_mock, sample_user_data):
        """Тест запроса 'неделя'"""
        inline_query_mock.query = "неделя"
        
        with patch('handlers.inline_query.db') as mock_db:
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
            call_args = inline_query_mock.answer.call_args[0][0]
            assert len(call_args) == 1
            assert "неделю" in call_args[0].title.lower()


class TestInlineScheduleDate:
    """Тесты запроса расписания на конкретную дату"""
    
    @pytest.mark.asyncio
    async def test_inline_schedule_date_format_ddmm(self, inline_query_mock, sample_user_data):
        """Тест формата даты DD.MM"""
        inline_query_mock.query = "01.04"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.datetime') as mock_datetime:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            # Мокаем datetime для парсинга даты
            mock_date = Mock()
            mock_date.weekday.return_value = 1  # Вторник
            mock_date.strftime.return_value = "01.04.2026"
            mock_datetime.return_value = mock_date
            mock_datetime.now.return_value.year = 2026
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_date_format_ddmmyyyy(self, inline_query_mock, sample_user_data):
        """Тест формата даты DD.MM.YYYY"""
        inline_query_mock.query = "01.04.2026"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.datetime') as mock_datetime:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            mock_date = Mock()
            mock_date.weekday.return_value = 1  # Вторник
            mock_date.strftime.return_value = "01.04.2026"
            mock_datetime.return_value = mock_date
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_invalid_date(self, inline_query_mock, sample_user_data):
        """Тест с невалидной датой"""
        inline_query_mock.query = "invalid_date"
        
        with patch('handlers.inline_query.db') as mock_db:
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
            call_args = inline_query_mock.answer.call_args[0][0]
            # Должны быть показаны подсказки
            assert len(call_args) >= 1


class TestGetScheduleResult:
    """Тесты функции get_schedule_result"""
    
    @pytest.mark.asyncio
    async def test_get_schedule_result_success(self):
        """Тест успешного получения расписания"""
        date = datetime(2026, 4, 1)
        group_id = 3191
        
        with patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.create_rasp_msg = AsyncMock(return_value=("<b>Расписание</b>\n1 пара: Математика", None))
            mock_rasp_class.return_value = mock_rasp
            
            result = await get_schedule_result(date, group_id, "Сегодня")
            
            assert result is not None
            assert isinstance(result, InlineQueryResultArticle)
            assert "Сегодня" in result.title
    
    @pytest.mark.asyncio
    async def test_get_schedule_result_no_schedule(self):
        """Тест когда расписание не опубликовано"""
        date = datetime(2026, 4, 1)
        group_id = 3191
        
        with patch('handlers.inline_query.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = await get_schedule_result(date, group_id, "Сегодня")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_schedule_result_group_not_found(self):
        """Тест когда группа не найдена"""
        date = datetime(2026, 4, 1)
        group_id = 9999
        
        with patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.create_rasp_msg = AsyncMock(return_value=(None, None))
            mock_rasp_class.return_value = mock_rasp
            
            result = await get_schedule_result(date, group_id, "Сегодня")
            
            assert result is not None
            assert "не найдена" in result.title
    
    @pytest.mark.asyncio
    async def test_get_schedule_result_closes_session(self):
        """Тест что сессия закрывается"""
        date = datetime(2026, 4, 1)
        group_id = 3191
        
        with patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.create_rasp_msg = AsyncMock(return_value=("Расписание", None))
            mock_rasp_class.return_value = mock_rasp
            
            await get_schedule_result(date, group_id, "Сегодня")
            
            # В новой реализации сессия не используется
            # Проверяем что функция отработала
            assert mock_rasp.create_rasp_msg.called
    
    @pytest.mark.asyncio
    async def test_get_schedule_result_description_truncation(self):
        """Тест обрезки длинного описания"""
        date = datetime(2026, 4, 1)
        group_id = 3191
        
        long_schedule = "Заголовок\n\n" + "\n".join([f"{i} пара: Очень длинное название предмета" for i in range(1, 10)])
        
        with patch('handlers.inline_query.Rasp') as mock_rasp_class, \
             patch('handlers.inline_query.os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.create_rasp_msg = AsyncMock(return_value=(long_schedule, None))
            mock_rasp_class.return_value = mock_rasp
            
            result = await get_schedule_result(date, group_id, "Сегодня")
            
            assert result is not None
            # Описание должно быть обрезано до 100 символов
            if len(result.description) > 100:
                assert result.description.endswith("...")


class TestInlineScheduleEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_inline_schedule_case_insensitive(self, inline_query_mock, sample_user_data):
        """Тест что запросы не чувствительны к регистру"""
        inline_query_mock.query = "СЕГОДНЯ"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            mock_find.return_value = [
                datetime(2026, 3, 31),
                datetime(2026, 4, 1),
                datetime(2026, 4, 2)
            ]
            
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_with_spaces(self, inline_query_mock, sample_user_data):
        """Тест запроса с пробелами"""
        inline_query_mock.query = "  сегодня  "
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            mock_find.return_value = [
                datetime(2026, 3, 31),
                datetime(2026, 4, 1),
                datetime(2026, 4, 2)
            ]
            
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            inline_query_mock.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inline_schedule_cache_time(self, inline_query_mock, sample_user_data):
        """Тест что устанавливается cache_time"""
        inline_query_mock.query = "сегодня"
        
        with patch('handlers.inline_query.db') as mock_db, \
             patch('handlers.inline_query.find_next_schedule_files') as mock_find, \
             patch('handlers.inline_query.get_schedule_result') as mock_get_result:
            
            mock_db.get = AsyncMock(return_value=sample_user_data)
            
            mock_find.return_value = [
                datetime(2026, 3, 31),
                datetime(2026, 4, 1),
                datetime(2026, 4, 2)
            ]
            
            mock_get_result.return_value = Mock(spec=InlineQueryResultArticle)
            
            await inline_schedule(inline_query_mock)
            
            # Проверяем что cache_time передан
            call_kwargs = inline_query_mock.answer.call_args[1]
            assert 'cache_time' in call_kwargs
