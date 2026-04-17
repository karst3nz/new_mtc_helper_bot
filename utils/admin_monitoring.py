"""
Система мониторинга для администратора
"""
import os
import psutil
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.db import DB
from utils.log import create_logger
from utils.admin_logger import get_error_logger

logger = create_logger(__name__)


class SystemMonitor:
    """Монитор системных ресурсов"""
    
    def __init__(self):
        self.db = DB()
        self.error_logger = get_error_logger()
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Получить статус системы
        
        Returns:
            Словарь с информацией о системе
        """
        try:
            status = {}
            
            # Использование памяти
            memory = psutil.virtual_memory()
            status['memory'] = {
                'total': self._format_bytes(memory.total),
                'used': self._format_bytes(memory.used),
                'available': self._format_bytes(memory.available),
                'percent': memory.percent
            }
            
            # Использование CPU
            status['cpu'] = {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count()
            }
            
            # Использование диска
            disk = shutil.disk_usage('/')
            status['disk'] = {
                'total': self._format_bytes(disk.total),
                'used': self._format_bytes(disk.used),
                'free': self._format_bytes(disk.free),
                'percent': (disk.used / disk.total) * 100
            }
            
            # Размер базы данных
            from config import db_DIR
            db_path = os.path.join(db_DIR, 'db.db')
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
                status['database'] = {
                    'size': self._format_bytes(db_size),
                    'size_bytes': db_size
                }
            else:
                status['database'] = {'size': 'N/A', 'size_bytes': 0}
            
            # Uptime процесса
            process = psutil.Process(os.getpid())
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - create_time
            status['uptime'] = {
                'seconds': int(uptime.total_seconds()),
                'formatted': self._format_uptime(uptime)
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {}
    
    def check_scheduler_status(self) -> Dict[str, Any]:
        """
        Проверить статус планировщика уведомлений
        
        Returns:
            Информация о планировщике
        """
        try:
            from utils.notifications import get_notification_manager
            
            notification_manager = get_notification_manager()
            
            status = {
                'running': notification_manager.scheduler.running,
                'jobs': []
            }
            
            if notification_manager.scheduler.running:
                jobs = notification_manager.scheduler.get_jobs()
                
                for job in jobs:
                    job_info = {
                        'id': job.id,
                        'name': job.name or job.id,
                        'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                        'next_run_formatted': job.next_run_time.strftime('%d.%m.%Y %H:%M:%S') if job.next_run_time else 'Не запланирован'
                    }
                    status['jobs'].append(job_info)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check scheduler status: {e}")
            return {'running': False, 'jobs': [], 'error': str(e)}
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить последние ошибки
        
        Args:
            limit: Максимальное количество
        
        Returns:
            Список ошибок
        """
        return self.error_logger.get_recent_errors(limit)
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Получить статистику ошибок
        
        Args:
            hours: Количество часов для анализа
        
        Returns:
            Статистика ошибок
        """
        try:
            # Частота ошибок
            frequency = self.error_logger.get_error_frequency(hours)
            
            # Ошибки по типам
            error_types = self.error_logger.get_error_stats(days=hours/24)
            
            return {
                'total': frequency,
                'by_type': error_types,
                'period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {'total': 0, 'by_type': {}, 'period_hours': hours}
    
    def check_health(self) -> Dict[str, Any]:
        """
        Комплексная проверка здоровья системы
        
        Returns:
            Результаты проверки
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'warnings': []
        }
        
        try:
            # Проверка памяти
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                health['issues'].append('Критически мало памяти (>90%)')
                health['status'] = 'critical'
            elif memory.percent > 80:
                health['warnings'].append('Высокое использование памяти (>80%)')
                if health['status'] == 'healthy':
                    health['status'] = 'warning'
            
            # Проверка диска
            disk = shutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 95:
                health['issues'].append('Критически мало места на диске (>95%)')
                health['status'] = 'critical'
            elif disk_percent > 85:
                health['warnings'].append('Мало места на диске (>85%)')
                if health['status'] == 'healthy':
                    health['status'] = 'warning'
            
            # Проверка планировщика
            scheduler_status = self.check_scheduler_status()
            if not scheduler_status.get('running'):
                health['issues'].append('Планировщик уведомлений не запущен')
                health['status'] = 'critical'
            
            # Проверка частоты ошибок
            error_stats = self.get_error_stats(hours=1)
            if error_stats['total'] > 50:
                health['issues'].append(f'Высокая частота ошибок ({error_stats["total"]} за час)')
                health['status'] = 'critical'
            elif error_stats['total'] > 20:
                health['warnings'].append(f'Повышенная частота ошибок ({error_stats["total"]} за час)')
                if health['status'] == 'healthy':
                    health['status'] = 'warning'
            
            # Проверка базы данных
            try:
                self.db.cursor.execute('SELECT COUNT(*) FROM users')
                self.db.cursor.fetchone()
            except Exception as e:
                health['issues'].append(f'Проблема с базой данных: {str(e)}')
                health['status'] = 'critical'
            
        except Exception as e:
            logger.error(f"Failed to check health: {e}")
            health['status'] = 'error'
            health['issues'].append(f'Ошибка проверки: {str(e)}')
        
        return health
    
    def format_system_status(self, status: Dict[str, Any]) -> str:
        """
        Форматирование статуса системы
        
        Args:
            status: Данные статуса
        
        Returns:
            Отформатированная строка
        """
        text = "⚙️ <b>СТАТУС СИСТЕМЫ</b>\n\n"
        
        # Память
        if 'memory' in status:
            mem = status['memory']
            text += f"💾 <b>Память:</b>\n"
            text += f"• Использовано: {mem['used']} / {mem['total']}\n"
            text += f"• Доступно: {mem['available']}\n"
            text += f"• Загрузка: <b>{mem['percent']}%</b>\n\n"
        
        # CPU
        if 'cpu' in status:
            cpu = status['cpu']
            text += f"🖥️ <b>Процессор:</b>\n"
            text += f"• Ядер: {cpu['count']}\n"
            text += f"• Загрузка: <b>{cpu['percent']}%</b>\n\n"
        
        # Диск
        if 'disk' in status:
            disk = status['disk']
            text += f"💿 <b>Диск:</b>\n"
            text += f"• Использовано: {disk['used']} / {disk['total']}\n"
            text += f"• Свободно: {disk['free']}\n"
            text += f"• Загрузка: <b>{disk['percent']:.1f}%</b>\n\n"
        
        # База данных
        if 'database' in status:
            db = status['database']
            text += f"🗄️ <b>База данных:</b>\n"
            text += f"• Размер: {db['size']}\n\n"
        
        # Uptime
        if 'uptime' in status:
            uptime = status['uptime']
            text += f"⏱️ <b>Время работы:</b> {uptime['formatted']}\n"
        
        return text
    
    def format_scheduler_status(self, status: Dict[str, Any]) -> str:
        """
        Форматирование статуса планировщика
        
        Args:
            status: Данные планировщика
        
        Returns:
            Отформатированная строка
        """
        text = "📊 <b>СТАТУС ПЛАНИРОВЩИКА</b>\n\n"
        
        if status.get('running'):
            text += "✅ Планировщик запущен и работает\n\n"
            
            jobs = status.get('jobs', [])
            if jobs:
                text += f"📋 <b>Активные задачи ({len(jobs)}):</b>\n\n"
                
                for job in jobs:
                    text += f"• <b>{job['name']}</b>\n"
                    text += f"  Следующий запуск: {job['next_run_formatted']}\n\n"
            else:
                text += "⚠️ Нет активных задач в планировщике\n"
        else:
            text += "❌ Планировщик не запущен!\n\n"
            
            if 'error' in status:
                text += f"Ошибка: {status['error']}\n\n"
            
            text += "Возможные причины:\n"
            text += "• Бот был перезапущен\n"
            text += "• Произошла ошибка при инициализации\n"
            text += "• Планировщик был остановлен вручную\n"
        
        return text
    
    def format_error_stats(self, stats: Dict[str, Any]) -> str:
        """
        Форматирование статистики ошибок
        
        Args:
            stats: Статистика
        
        Returns:
            Отформатированная строка
        """
        text = f"⚠️ <b>СТАТИСТИКА ОШИБОК</b>\n"
        text += f"<i>За последние {stats['period_hours']} часов</i>\n\n"
        
        text += f"<b>Всего ошибок:</b> {stats['total']}\n\n"
        
        if stats['by_type']:
            text += "<b>По типам:</b>\n"
            for error_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
                text += f"• {error_type}: <b>{count}</b>\n"
        else:
            text += "✅ Ошибок не обнаружено\n"
        
        return text
    
    def format_health_check(self, health: Dict[str, Any]) -> str:
        """
        Форматирование результатов проверки здоровья
        
        Args:
            health: Результаты проверки
        
        Returns:
            Отформатированная строка
        """
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'error': '❌'
        }
        
        emoji = status_emoji.get(health['status'], '❓')
        
        text = f"{emoji} <b>ПРОВЕРКА ЗДОРОВЬЯ СИСТЕМЫ</b>\n\n"
        text += f"<b>Статус:</b> {health['status'].upper()}\n\n"
        
        if health['issues']:
            text += "🚨 <b>Критические проблемы:</b>\n"
            for issue in health['issues']:
                text += f"• {issue}\n"
            text += "\n"
        
        if health['warnings']:
            text += "⚠️ <b>Предупреждения:</b>\n"
            for warning in health['warnings']:
                text += f"• {warning}\n"
            text += "\n"
        
        if not health['issues'] and not health['warnings']:
            text += "✅ Все системы работают нормально\n"
        
        return text
    
    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """Форматирование байтов в читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    @staticmethod
    def _format_uptime(uptime: timedelta) -> str:
        """Форматирование времени работы"""
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}с")
        
        return " ".join(parts)


class QuickActions:
    """Быстрые действия для администратора"""
    
    def __init__(self):
        self.db = DB()
        from utils.admin_logger import get_admin_logger
        self.admin_logger = get_admin_logger()
    
    async def restart_scheduler(self, admin_id: int) -> bool:
        """
        Перезапустить планировщик уведомлений
        
        Args:
            admin_id: ID администратора
        
        Returns:
            True если успешно
        """
        try:
            from utils.notifications import get_notification_manager
            
            notification_manager = get_notification_manager()
            
            # Останавливаем
            notification_manager.stop()
            
            # Запускаем заново
            notification_manager.start()
            
            # Логируем
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='scheduler_restart'
            )
            
            logger.info(f"Scheduler restarted by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart scheduler: {e}")
            return False
    
    def clear_cache(self, admin_id: int) -> bool:
        """
        Очистить кэш (временные файлы расписаний)
        
        Args:
            admin_id: ID администратора
        
        Returns:
            True если успешно
        """
        try:
            import glob
            
            # Очищаем временные файлы
            cache_patterns = [
                'data/htm/*.htm',
                'data/htm/*.html'
            ]
            
            deleted_count = 0
            for pattern in cache_patterns:
                files = glob.glob(pattern)
                for file in files:
                    try:
                        os.remove(file)
                        deleted_count += 1
                    except:
                        pass
            
            # Логируем
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='cache_clear',
                details={'deleted_files': deleted_count}
            )
            
            logger.info(f"Cache cleared by admin {admin_id}, deleted {deleted_count} files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    async def update_all_schedules(self, admin_id: int) -> Dict[str, int]:
        """
        Обновить все расписания
        
        Args:
            admin_id: ID администратора
        
        Returns:
            Статистика обновления
        """
        try:
            from utils.rasp import Rasp
            from config import groups
            from datetime import datetime
            
            stats = {'success': 0, 'failed': 0}
            
            # Обновляем расписание на сегодня для всех групп
            date_str = datetime.now().strftime("%d_%m_%Y")
            
            for group in groups[:5]:  # Ограничиваем для примера
                try:
                    rasp = Rasp(date=date_str)
                    await rasp.run_session()
                    await rasp.get()
                    await rasp.close_session()
                    stats['success'] += 1
                except:
                    stats['failed'] += 1
            
            # Логируем
            self.admin_logger.log_action(
                admin_id=admin_id,
                action='schedules_update',
                details=stats
            )
            
            logger.info(f"Schedules updated by admin {admin_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to update schedules: {e}")
            return {'success': 0, 'failed': 0}


# Глобальные экземпляры
_system_monitor = None
_quick_actions = None


def get_system_monitor() -> SystemMonitor:
    """Получить глобальный экземпляр SystemMonitor"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def get_quick_actions() -> QuickActions:
    """Получить глобальный экземпляр QuickActions"""
    global _quick_actions
    if _quick_actions is None:
        _quick_actions = QuickActions()
    return _quick_actions
