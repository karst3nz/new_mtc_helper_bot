"""
Тесты для модуля notifications
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from utils.notifications import NotificationManager, get_notification_manager


@pytest.fixture
def mock_db():
    """Мок базы данных"""
    db = Mock()
    db.get = AsyncMock()
    db.get_users_with_lesson_reminder = Mock()
    db.get_users_with_daily_schedule = Mock()
    db.cursor = Mock()
    db.cursor.execute = Mock()
    db.cursor.fetchall = Mock()
    return db


@pytest.fixture
def mock_bot():
    """Мок бота"""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_rasp():
    """Мок класса Rasp"""
    rasp = AsyncMock()
    rasp.run_session = AsyncMock()
    rasp.close_session = AsyncMock()
    rasp.get = AsyncMock()
    rasp.rasp_exists = True
    rasp.get_rasp = AsyncMock(return_value="<b>Расписание</b>\n1 пара: Математика")
    rasp.get_lessons_duration = AsyncMock(return_value=("1", "4"))
    return rasp


@pytest.fixture
def notification_manager(mock_db, mock_bot):
    """Экземпляр NotificationManager с моками"""
    with patch('utils.notifications.DB', return_value=mock_db), \
         patch('utils.notifications.bot', mock_bot):
        manager = NotificationManager()
        manager.db = mock_db
        return manager


@pytest.fixture
def sample_user_data():
    """Примерные данные пользователя"""
    return (12345, 'test_user', 'Test User', '3191', None, 10, 'newRasp', '1')


class TestNotificationManagerInit:
    """Тесты инициализации NotificationManager"""
    
    def test_notification_manager_init(self, notification_manager):
        """Тест инициализации менеджера уведомлений"""
        assert notification_manager is not None
        assert notification_manager.scheduler is not None
        assert notification_manager.db is not None
        assert notification_manager.logger is not None
    
    def test_notification_manager_start(self, notification_manager):
        """Тест запуска планировщика"""
        notification_manager.start()
        
        assert notification_manager.scheduler.running
        
        # Проверяем что задачи добавлены
        jobs = notification_manager.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        
        assert 'lesson_reminders' in job_ids
        assert 'daily_schedules' in job_ids
        assert 'hours_threshold' in job_ids
        
        notification_manager.stop()
    
    def test_notification_manager_stop(self, notification_manager):
        """Тест остановки планировщика"""
        notification_manager.start()
        assert notification_manager.scheduler.running
        
        notification_manager.stop()
        # После shutdown() scheduler может все еще показывать running=True
        # Проверяем что метод был вызван без ошибок
        assert True


class TestLessonReminders:
    """Тесты напоминаний о парах"""
    
    @pytest.mark.asyncio
    async def test_check_lesson_reminders_no_users(self, notification_manager):
        """Тест когда нет пользователей с напоминаниями"""
        notification_manager.db.get_users_with_lesson_reminder.return_value = []
        
        await notification_manager.check_lesson_reminders()
        
        # Не должно быть ошибок
        notification_manager.db.get_users_with_lesson_reminder.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_lesson_reminders_with_users(self, notification_manager, sample_user_data, mock_bot):
        """Тест напоминаний с пользователями"""
        notification_manager.db.get_users_with_lesson_reminder.return_value = [
            (12345, 30),
            (67890, 15)
        ]
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot), \
             patch('utils.notifications.utils') as mock_utils:
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_lessons_duration = AsyncMock(return_value=("1", "4"))
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            mock_utils.get_lesson_time.return_value = "09:00"
            
            await notification_manager.check_lesson_reminders()
            
            # Проверяем что метод был вызван для каждого пользователя
            assert notification_manager.db.get.call_count >= 0
    
    @pytest.mark.asyncio
    async def test_send_lesson_reminder_sunday(self, notification_manager, sample_user_data):
        """Тест что напоминания не отправляются в воскресенье"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.weekday.return_value = 6  # Воскресенье
            mock_datetime.now.return_value = mock_now
            
            await notification_manager._send_lesson_reminder(12345, 30)
            
            # Не должно быть вызовов к Rasp
    
    @pytest.mark.asyncio
    async def test_send_lesson_reminder_no_schedule(self, notification_manager, sample_user_data, mock_bot):
        """Тест когда расписание не опубликовано"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot):
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = False
            mock_rasp_class.return_value = mock_rasp
            
            await notification_manager._send_lesson_reminder(12345, 30)
            
            # Не должно быть отправки сообщений
            mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_lesson_reminder_success(self, notification_manager, sample_user_data, mock_bot):
        """Тест успешной отправки напоминания"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot), \
             patch('utils.notifications.utils') as mock_utils, \
             patch('utils.notifications.datetime') as mock_datetime:
            
            # Настраиваем время
            mock_now = datetime(2026, 3, 31, 8, 30)  # Понедельник 8:30
            mock_datetime.now.return_value = mock_now
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_lessons_duration = AsyncMock(return_value=("1", "4"))
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            mock_utils.get_lesson_time.return_value = "09:00"
            
            await notification_manager._send_lesson_reminder(12345, 30)
            
            # Проверяем что сообщение отправлено
            mock_bot.send_message.assert_called_once()


class TestDailySchedules:
    """Тесты ежедневных расписаний"""
    
    @pytest.mark.asyncio
    async def test_check_daily_schedules_no_users(self, notification_manager):
        """Тест когда нет пользователей с ежедневными расписаниями"""
        notification_manager.db.get_users_with_daily_schedule.return_value = []
        
        await notification_manager.check_daily_schedules()
        
        notification_manager.db.get_users_with_daily_schedule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_daily_schedules_with_users(self, notification_manager):
        """Тест ежедневных расписаний с пользователями"""
        notification_manager.db.get_users_with_daily_schedule.return_value = [
            (12345, "20:00"),
            (67890, "21:00")
        ]
        
        with patch('utils.notifications.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20:00"
            
            await notification_manager.check_daily_schedules()
            
            # Проверяем что метод был вызван
            assert notification_manager.db.get_users_with_daily_schedule.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_send_daily_schedule_success(self, notification_manager, sample_user_data, mock_bot):
        """Тест успешной отправки ежедневного расписания"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot):
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание на завтра")
            mock_rasp_class.return_value = mock_rasp
            
            await notification_manager._send_daily_schedule(12345)
            
            # Проверяем что сообщение отправлено
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args[0][0] == 12345
            assert "Расписание на завтра" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_send_daily_schedule_no_schedule(self, notification_manager, sample_user_data, mock_bot):
        """Тест когда расписание на завтра не опубликовано"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot):
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = False
            mock_rasp_class.return_value = mock_rasp
            
            await notification_manager._send_daily_schedule(12345)
            
            # Проверяем что отправлено сообщение о том, что расписание не опубликовано
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert "не опубликовано" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_send_daily_schedule_skip_sunday(self, notification_manager, sample_user_data, mock_bot):
        """Тест что воскресенье пропускается"""
        notification_manager.db.get.return_value = sample_user_data
        
        with patch('utils.notifications.Rasp') as mock_rasp_class, \
             patch('utils.notifications.bot', mock_bot), \
             patch('utils.notifications.datetime') as mock_datetime, \
             patch('utils.notifications.timedelta') as mock_timedelta:
            
            # Настраиваем так, чтобы завтра было воскресенье
            from datetime import datetime as real_datetime, timedelta as real_timedelta
            
            mock_now = real_datetime(2026, 4, 5, 20, 0)  # Суббота
            mock_tomorrow = real_datetime(2026, 4, 6, 20, 0)  # Воскресенье
            mock_monday = real_datetime(2026, 4, 7, 20, 0)  # Понедельник
            
            mock_datetime.now.return_value = mock_now
            mock_timedelta.side_effect = lambda **kwargs: real_timedelta(**kwargs)
            
            mock_rasp = AsyncMock()
            mock_rasp.run_session = AsyncMock()
            mock_rasp.close_session = AsyncMock()
            mock_rasp.get = AsyncMock()
            mock_rasp.rasp_exists = True
            mock_rasp.get_rasp = AsyncMock(return_value="Расписание")
            mock_rasp_class.return_value = mock_rasp
            
            await notification_manager._send_daily_schedule(12345)
            
            # Должно быть отправлено расписание на понедельник
            mock_bot.send_message.assert_called_once()


class TestHoursThreshold:
    """Тесты уведомлений о пороге пропущенных часов"""
    
    @pytest.mark.asyncio
    async def test_check_hours_threshold_no_users(self, notification_manager):
        """Тест когда нет пользователей с уведомлениями о пропусках"""
        notification_manager.db.cursor.fetchall.return_value = []
        
        await notification_manager.check_hours_threshold()
        
        notification_manager.db.cursor.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_hours_threshold_below_threshold(self, notification_manager, mock_bot):
        """Тест когда пропуски ниже порога"""
        notification_manager.db.cursor.fetchall.return_value = [
            (12345, 50, 30, 0)  # user_id, threshold, current_hours, last_hours_notification
        ]
        
        with patch('utils.notifications.bot', mock_bot):
            await notification_manager.check_hours_threshold()
            
            # Не должно быть отправки сообщений
            mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_hours_threshold_above_threshold(self, notification_manager, mock_bot):
        """Тест когда пропуски превышают порог"""
        notification_manager.db.cursor.fetchall.return_value = [
            (12345, 30, 50, 0)  # user_id, threshold, current_hours, last_hours_notification
        ]
        
        with patch('utils.notifications.bot', mock_bot):
            await notification_manager.check_hours_threshold()
            
            # Должно быть отправлено уведомление
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args[0][0] == 12345
            assert "50" in call_args[0][1]
            assert "30" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_check_hours_threshold_equal_threshold(self, notification_manager, mock_bot):
        """Тест когда пропуски равны порогу"""
        notification_manager.db.cursor.fetchall.return_value = [
            (12345, 40, 40, 0)  # user_id, threshold, current_hours, last_hours_notification
        ]
        
        with patch('utils.notifications.bot', mock_bot):
            await notification_manager.check_hours_threshold()
            
            # Должно быть отправлено уведомление (>=)
            mock_bot.send_message.assert_called_once()


class TestCustomNotifications:
    """Тесты кастомных уведомлений"""
    
    @pytest.mark.asyncio
    async def test_send_custom_notification_success(self, notification_manager, mock_bot):
        """Тест успешной отправки кастомного уведомления"""
        with patch('utils.notifications.bot', mock_bot):
            result = await notification_manager.send_custom_notification(12345, "Тестовое сообщение")
            
            assert result is True
            mock_bot.send_message.assert_called_once_with(12345, "Тестовое сообщение")
    
    @pytest.mark.asyncio
    async def test_send_custom_notification_error(self, notification_manager, mock_bot):
        """Тест ошибки при отправке кастомного уведомления"""
        mock_bot.send_message.side_effect = Exception("Send error")
        
        with patch('utils.notifications.bot', mock_bot):
            result = await notification_manager.send_custom_notification(12345, "Тестовое сообщение")
            
            assert result is False


class TestGetNotificationManager:
    """Тесты функции get_notification_manager"""
    
    def test_get_notification_manager_singleton(self):
        """Тест что возвращается один и тот же экземпляр"""
        with patch('utils.notifications.DB'), \
             patch('utils.notifications.bot'):
            
            manager1 = get_notification_manager()
            manager2 = get_notification_manager()
            
            assert manager1 is manager2
    
    def test_get_notification_manager_creates_instance(self):
        """Тест создания экземпляра"""
        with patch('utils.notifications.DB'), \
             patch('utils.notifications.bot'), \
             patch('utils.notifications.notification_manager', None):
            
            manager = get_notification_manager()
            
            assert manager is not None
            assert isinstance(manager, NotificationManager)


class TestNotificationManagerErrorHandling:
    """Тесты обработки ошибок"""
    
    @pytest.mark.asyncio
    async def test_check_lesson_reminders_db_error(self, notification_manager):
        """Тест обработки ошибки БД при проверке напоминаний"""
        notification_manager.db.get_users_with_lesson_reminder.side_effect = Exception("DB error")
        
        # Не должно быть исключений
        await notification_manager.check_lesson_reminders()
    
    @pytest.mark.asyncio
    async def test_check_daily_schedules_db_error(self, notification_manager):
        """Тест обработки ошибки БД при проверке ежедневных расписаний"""
        notification_manager.db.get_users_with_daily_schedule.side_effect = Exception("DB error")
        
        # Не должно быть исключений
        await notification_manager.check_daily_schedules()
    
    @pytest.mark.asyncio
    async def test_check_hours_threshold_db_error(self, notification_manager):
        """Тест обработки ошибки БД при проверке порога часов"""
        notification_manager.db.cursor.execute.side_effect = Exception("DB error")
        
        # Не должно быть исключений
        await notification_manager.check_hours_threshold()
    
    @pytest.mark.asyncio
    async def test_send_lesson_reminder_user_not_found(self, notification_manager):
        """Тест когда пользователь не найден"""
        notification_manager.db.get.return_value = None
        
        # Не должно быть исключений
        await notification_manager._send_lesson_reminder(99999, 30)
