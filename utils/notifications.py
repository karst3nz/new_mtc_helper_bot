"""
Система уведомлений для бота
"""
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.db import DB
from utils.rasp import Rasp
from utils.log import create_logger
from config import bot, groups
from utils import utils


class NotificationManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db = DB()
        self.logger = create_logger(__name__)
        self.logger.info("NotificationManager инициализирован")
    
    def start(self):
        """Запуск планировщика уведомлений"""
        self.logger.info("Запуск планировщика уведомлений")
        
        # Проверка напоминаний о парах каждые 5 минут
        self.scheduler.add_job(
            self.check_lesson_reminders,
            'interval',
            minutes=5,
            id='lesson_reminders'
        )
        
        # Проверка ежедневных расписаний каждый час
        self.scheduler.add_job(
            self.check_daily_schedules,
            'interval',
            hours=1,
            id='daily_schedules'
        )
        
        # Проверка порога пропущенных часов раз в день в 9:00
        self.scheduler.add_job(
            self.check_hours_threshold,
            CronTrigger(hour=9, minute=0),
            id='hours_threshold'
        )
        
        self.scheduler.start()
        self.logger.info("Планировщик уведомлений запущен")
    
    def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        self.logger.info("Планировщик уведомлений остановлен")
    
    async def check_lesson_reminders(self):
        """Проверка и отправка напоминаний о парах"""
        self.logger.debug("Проверка напоминаний о парах")
        
        try:
            users = self.db.get_users_with_lesson_reminder()
            
            for user_id, reminder_minutes in users:
                try:
                    await self._send_lesson_reminder(user_id, reminder_minutes)
                except Exception as e:
                    self.logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка в check_lesson_reminders: {e}")
    
    async def _send_lesson_reminder(self, user_id: int, reminder_minutes: int):
        """Отправить напоминание о паре конкретному пользователю"""
        user_data = await self.db.get(user_id)
        if not user_data:
            return
        
        group_id = user_data[3]
        smena = user_data[7] if user_data[7] else "1"
        
        # Получаем расписание на сегодня
        today = datetime.now()
        
        # Пропускаем воскресенье
        if today.weekday() == 6:
            return
        
        date_str = today.strftime("%d_%m_%Y")
        
        rasp = Rasp(date=date_str)
        await rasp.run_session()
        
        try:
            await rasp.get()
            
            if not rasp.rasp_exists:
                return
            
            # Получаем время первой и последней пары
            first_num, last_num = await rasp.get_lessons_duration(str(group_id))
            
            if not first_num:
                return
            
            # Получаем время начала первой пары
            is_weekend = today.weekday() == 5  # Суббота
            lesson_time = utils.get_lesson_time(
                str(first_num), 
                True,  # start=True для времени начала
                not is_weekend,  # weekday=True для будних дней
                str(smena)
            )
            
            if not lesson_time:
                self.logger.warning(f"Не удалось получить время пары для пользователя {user_id}")
                return
            
            # Парсим время пары
            try:
                lesson_hour, lesson_minute = map(int, lesson_time.split(":"))
            except (ValueError, AttributeError) as e:
                self.logger.error(f"Ошибка парсинга времени пары '{lesson_time}': {e}")
                return
            
            lesson_datetime = today.replace(hour=lesson_hour, minute=lesson_minute, second=0, microsecond=0)
            
            # Вычисляем время напоминания
            reminder_time = lesson_datetime - timedelta(minutes=reminder_minutes)
            current_time = datetime.now()
            
            # Проверяем, нужно ли отправить напоминание сейчас (в пределах 5 минут)
            time_diff = abs((current_time - reminder_time).total_seconds())
            
            if time_diff <= 300:  # 5 минут = 300 секунд
                rasp_text = await rasp.get_rasp(group=str(group_id))
                
                if rasp_text:
                    message = (
                        f"🔔 <b>Напоминание о парах!</b>\n\n"
                        f"Через {reminder_minutes} минут начинаются пары:\n\n"
                        f"{rasp_text}"
                    )
                    
                    await bot.send_message(user_id, message)
                    self.logger.info(f"Отправлено напоминание пользователю {user_id}")
        
        finally:
            await rasp.close_session()
    
    async def check_daily_schedules(self):
        """Проверка и отправка ежедневных расписаний"""
        self.logger.debug("Проверка ежедневных расписаний")
        
        try:
            users = self.db.get_users_with_daily_schedule()
            current_time = datetime.now().strftime("%H:%M")
            
            for user_id, schedule_time in users:
                # Проверяем, совпадает ли текущее время с настроенным (с точностью до часа)
                if current_time.split(":")[0] == schedule_time.split(":")[0]:
                    try:
                        await self._send_daily_schedule(user_id)
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки ежедневного расписания пользователю {user_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка в check_daily_schedules: {e}")
    
    async def _send_daily_schedule(self, user_id: int):
        """Отправить ежедневное расписание на завтра"""
        user_data = await self.db.get(user_id)
        if not user_data:
            return
        
        group_id = user_data[3]
        
        # Получаем расписание на завтра
        tomorrow = datetime.now() + timedelta(days=1)
        
        # Пропускаем воскресенье
        if tomorrow.weekday() == 6:
            tomorrow = tomorrow + timedelta(days=1)
        
        date_str = tomorrow.strftime("%d_%m_%Y")
        
        rasp = Rasp(date=date_str)
        await rasp.run_session()
        
        try:
            await rasp.get()
            
            if not rasp.rasp_exists:
                message = f"📅 Расписание на завтра ({tomorrow.strftime('%d.%m.%Y')}) еще не опубликовано"
                await bot.send_message(user_id, message)
                return
            
            rasp_text = await rasp.get_rasp(group=str(group_id))
            
            if rasp_text:
                weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
                weekday = weekday_names[tomorrow.weekday()]
                
                message = (
                    f"📅 <b>Расписание на завтра</b>\n"
                    f"{weekday}, {tomorrow.strftime('%d.%m.%Y')}\n\n"
                    f"{rasp_text}"
                )
                
                # Добавляем информацию о пропущенных часах если нужно
                missed_hours = int(user_data[5]) if user_data[5] else 0
                show_mode = user_data[6]
                
                if show_mode and "newRasp" in show_mode and missed_hours > 0:
                    message += f"\n\n⏰ У тебя сейчас <b>{missed_hours}</b> пропущенных часов."
                
                await bot.send_message(user_id, message)
                self.logger.info(f"Отправлено ежедневное расписание пользователю {user_id}")
        
        finally:
            await rasp.close_session()
    
    async def check_hours_threshold(self):
        """Проверка порога пропущенных часов"""
        self.logger.debug("Проверка порога пропущенных часов")
        
        try:
            # Получаем всех пользователей с включенными уведомлениями о пропусках
            self.db.cursor.execute(
                """
                SELECT ns.user_id, ns.hours_threshold, u.missed_hours, ns.last_hours_notification
                FROM notification_settings ns
                JOIN users u ON ns.user_id = u.user_id
                WHERE ns.hours_notification = 1
                """
            )
            users = self.db.cursor.fetchall()
            
            for user_id, threshold, current_hours, last_notified_hours in users:
                # Отправляем уведомление только если:
                # 1. Текущие часы >= порога
                # 2. Последнее уведомление было при меньшем количестве часов (или не было вообще)
                if current_hours >= threshold and current_hours > last_notified_hours:
                    try:
                        message = (
                            f"⚠️ <b>Внимание!</b>\n\n"
                            f"У вас накопилось <b>{current_hours}</b> пропущенных часов.\n"
                            f"Это превышает установленный порог ({threshold} часов).\n\n"
                        )
                        
                        await bot.send_message(user_id, message)
                        
                        # Обновляем значение последнего уведомления
                        self.db.update_notification_setting(user_id, "last_hours_notification", current_hours)
                        
                        self.logger.info(f"Отправлено уведомление о пропусках пользователю {user_id}")
                    
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки уведомления о пропусках пользователю {user_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка в check_hours_threshold: {e}")
    
    async def send_custom_notification(self, user_id: int, message: str):
        """Отправить кастомное уведомление пользователю"""
        try:
            await bot.send_message(user_id, message)
            self.logger.info(f"Отправлено кастомное уведомление пользователю {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка отправки кастомного уведомления пользователю {user_id}: {e}")
            return False


# Глобальный экземпляр менеджера уведомлений
notification_manager = None


def get_notification_manager():
    """Получить глобальный экземпляр менеджера уведомлений"""
    global notification_manager
    if notification_manager is None:
        notification_manager = NotificationManager()
    return notification_manager
