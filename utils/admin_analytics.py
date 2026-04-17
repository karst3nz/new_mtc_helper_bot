"""
Система аналитики и статистики для администратора
"""
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import Counter
import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams

from utils.db import DB
from utils.log import create_logger

logger = create_logger(__name__)

# Настройка шрифтов для поддержки кириллицы
rcParams['font.family'] = 'DejaVu Sans'


class AnalyticsManager:
    """Менеджер аналитики и статистики"""
    
    def __init__(self):
        self.db = DB()
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Получить ключевые метрики для дашборда
        
        Returns:
            Словарь с метриками
        """
        try:
            metrics = {}
            
            # Общее количество пользователей
            self.db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 0')
            metrics['total_users'] = self.db.cursor.fetchone()[0]
            
            # Заблокированные пользователи
            self.db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 1')
            metrics['blocked_users'] = self.db.cursor.fetchone()[0]
            
            # Активные за день
            day_ago = datetime.now() - timedelta(days=1)
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_blocked = 0',
                (day_ago.isoformat(),)
            )
            metrics['active_day'] = self.db.cursor.fetchone()[0]
            
            # Активные за неделю
            week_ago = datetime.now() - timedelta(days=7)
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_blocked = 0',
                (week_ago.isoformat(),)
            )
            metrics['active_week'] = self.db.cursor.fetchone()[0]
            
            # Активные за месяц
            month_ago = datetime.now() - timedelta(days=30)
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_blocked = 0',
                (month_ago.isoformat(),)
            )
            metrics['active_month'] = self.db.cursor.fetchone()[0]
            
            # Новые пользователи за неделю
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE created_at >= ?',
                (week_ago.isoformat(),)
            )
            metrics['new_week'] = self.db.cursor.fetchone()[0]
            
            # Новые пользователи за месяц
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE created_at >= ?',
                (month_ago.isoformat(),)
            )
            metrics['new_month'] = self.db.cursor.fetchone()[0]
            
            # Топ групп
            self.db.cursor.execute(
                '''SELECT group_id, COUNT(*) as count 
                   FROM users 
                   WHERE group_id IS NOT NULL AND is_blocked = 0
                   GROUP BY group_id 
                   ORDER BY count DESC 
                   LIMIT 5'''
            )
            metrics['top_groups'] = [(row[0], row[1]) for row in self.db.cursor.fetchall()]
            
            # Средние пропуски
            self.db.cursor.execute(
                'SELECT AVG(missed_hours) FROM users WHERE is_blocked = 0'
            )
            avg_hours = self.db.cursor.fetchone()[0]
            metrics['avg_missed_hours'] = round(avg_hours, 1) if avg_hours else 0
            
            # Средние пропуски по группам (топ 5)
            self.db.cursor.execute(
                '''SELECT group_id, AVG(missed_hours) as avg_hours
                   FROM users
                   WHERE group_id IS NOT NULL AND is_blocked = 0
                   GROUP BY group_id
                   ORDER BY avg_hours DESC
                   LIMIT 5'''
            )
            metrics['top_groups_by_hours'] = [(row[0], round(row[1], 1)) for row in self.db.cursor.fetchall()]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {}
    
    def get_user_growth_data(self, days: int = 30) -> List[Tuple[str, int]]:
        """
        Получить данные роста пользователей
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Список кортежей (дата, количество)
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            self.db.cursor.execute(
                '''SELECT DATE(created_at) as date, COUNT(*) as count
                   FROM users
                   WHERE created_at IS NOT NULL AND created_at >= ?
                   GROUP BY DATE(created_at)
                   ORDER BY date''',
                (start_date.isoformat(),)
            )
            
            rows = self.db.cursor.fetchall()
            logger.info(f"User growth data: found {len(rows)} data points for last {days} days")
            
            return [(row[0], row[1]) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get user growth data: {e}", exc_info=True)
            return []
    
    def generate_user_growth_chart(self, days: int = 30) -> Optional[bytes]:
        """
        Создать график роста пользователей
        
        Args:
            days: Количество дней
        
        Returns:
            Изображение в байтах
        """
        try:
            data = self.get_user_growth_data(days)
            
            logger.info(f"Generating user growth chart with {len(data)} data points")
            
            if not data:
                logger.warning("No data available for user growth chart")
                return None
            
            # Подготовка данных
            dates = [datetime.fromisoformat(d[0]) for d in data]
            counts = [d[1] for d in data]
            
            logger.info(f"Chart data prepared: {len(dates)} dates, {len(counts)} counts")
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(dates, counts, marker='o', linewidth=2, markersize=6, color='#2196F3')
            
            # Настройка осей
            ax.set_xlabel('Дата', fontsize=12)
            ax.set_ylabel('Новых пользователей', fontsize=12)
            ax.set_title(f'Рост пользователей за {days} дней', fontsize=14, fontweight='bold')
            
            # Форматирование дат
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
            plt.xticks(rotation=45)
            
            # Сетка
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Плотная компоновка
            plt.tight_layout()
            
            # Сохранение в байты
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            chart_bytes = buf.getvalue()
            logger.info(f"Chart generated successfully, size: {len(chart_bytes)} bytes")
            
            return chart_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate user growth chart: {e}", exc_info=True)
            return None
    
    def get_activity_by_hour(self) -> List[Tuple[int, int]]:
        """
        Получить активность по часам суток
        
        Returns:
            Список кортежей (час, количество)
        """
        try:
            # Получаем активность за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            
            self.db.cursor.execute(
                '''SELECT timestamp FROM user_activity
                   WHERE timestamp >= ?''',
                (week_ago.isoformat(),)
            )
            
            # Подсчитываем по часам
            hours = [0] * 24
            for row in self.db.cursor.fetchall():
                try:
                    dt = datetime.fromisoformat(row[0])
                    hours[dt.hour] += 1
                except:
                    pass
            
            return [(h, count) for h, count in enumerate(hours)]
            
        except Exception as e:
            logger.error(f"Failed to get activity by hour: {e}")
            return [(h, 0) for h in range(24)]
    
    def generate_activity_chart(self) -> Optional[bytes]:
        """
        Создать график активности по часам
        
        Returns:
            Изображение в байтах
        """
        try:
            data = self.get_activity_by_hour()
            
            hours = [d[0] for d in data]
            counts = [d[1] for d in data]
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(hours, counts, color='#4CAF50', alpha=0.7, edgecolor='black')
            
            # Подсветка пиковых часов
            max_count = max(counts)
            for i, bar in enumerate(bars):
                if counts[i] == max_count:
                    bar.set_color('#FF5722')
            
            # Настройка осей
            ax.set_xlabel('Час суток', fontsize=12)
            ax.set_ylabel('Количество действий', fontsize=12)
            ax.set_title('Активность пользователей по часам (за 7 дней)', fontsize=14, fontweight='bold')
            ax.set_xticks(hours)
            ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45)
            
            # Сетка
            ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            plt.tight_layout()
            
            # Сохранение
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate activity chart: {e}")
            return None
    
    def get_hours_distribution(self) -> List[Tuple[str, int]]:
        """
        Получить распределение пропущенных часов
        
        Returns:
            Список кортежей (диапазон, количество)
        """
        try:
            self.db.cursor.execute(
                'SELECT missed_hours FROM users WHERE is_blocked = 0'
            )
            
            # Преобразуем в int, обрабатываем None и строки
            hours_list = []
            for row in self.db.cursor.fetchall():
                try:
                    hours = row[0]
                    if hours is None:
                        hours_list.append(0)
                    elif isinstance(hours, str):
                        hours_list.append(int(hours) if hours.isdigit() else 0)
                    else:
                        hours_list.append(int(hours))
                except (ValueError, TypeError):
                    hours_list.append(0)
            
            # Группируем по диапазонам
            ranges = {
                '0': 0,
                '1-5': 0,
                '6-10': 0,
                '11-20': 0,
                '21-30': 0,
                '31-50': 0,
                '50+': 0
            }
            
            for hours in hours_list:
                if hours == 0:
                    ranges['0'] += 1
                elif 1 <= hours <= 5:
                    ranges['1-5'] += 1
                elif 6 <= hours <= 10:
                    ranges['6-10'] += 1
                elif 11 <= hours <= 20:
                    ranges['11-20'] += 1
                elif 21 <= hours <= 30:
                    ranges['21-30'] += 1
                elif 31 <= hours <= 50:
                    ranges['31-50'] += 1
                else:
                    ranges['50+'] += 1
            
            return list(ranges.items())
            
        except Exception as e:
            logger.error(f"Failed to get hours distribution: {e}", exc_info=True)
            return []
    
    def generate_hours_distribution_chart(self) -> Optional[bytes]:
        """
        Создать график распределения пропусков
        
        Returns:
            Изображение в байтах
        """
        try:
            data = self.get_hours_distribution()
            
            labels = [d[0] for d in data]
            counts = [d[1] for d in data]
            
            # Цвета от зеленого к красному
            colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFC107', '#FF9800', '#FF5722', '#F44336']
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(labels, counts, color=colors, alpha=0.8, edgecolor='black')
            
            # Добавляем значения на столбцы
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # Настройка осей
            ax.set_xlabel('Пропущенные часы', fontsize=12)
            ax.set_ylabel('Количество пользователей', fontsize=12)
            ax.set_title('Распределение пропущенных часов', fontsize=14, fontweight='bold')
            
            # Сетка
            ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            plt.tight_layout()
            
            # Сохранение
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate hours distribution chart: {e}")
            return None
    
    def get_command_usage_stats(self, days: int = 7) -> List[Tuple[str, int]]:
        """
        Получить статистику использования команд
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Список кортежей (команда, количество)
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            self.db.cursor.execute(
                '''SELECT action, COUNT(*) as count
                   FROM user_activity
                   WHERE timestamp >= ? AND action LIKE '/%%'
                   GROUP BY action
                   ORDER BY count DESC
                   LIMIT 10''',
                (start_date.isoformat(),)
            )
            
            return [(row[0], row[1]) for row in self.db.cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get command usage stats: {e}")
            return []
    
    def format_dashboard(self, metrics: Dict[str, Any]) -> str:
        """
        Форматирование дашборда для отображения
        
        Args:
            metrics: Метрики
        
        Returns:
            Отформатированная строка
        """
        text = "📊 <b>ДАШБОРД АНАЛИТИКИ</b>\n\n"
        
        text += "👥 <b>Пользователи:</b>\n"
        text += f"• Всего: <b>{metrics.get('total_users', 0)}</b>\n"
        text += f"• Заблокировано: <b>{metrics.get('blocked_users', 0)}</b>\n\n"
        
        text += "⚡ <b>Активность:</b>\n"
        text += f"• За день: <b>{metrics.get('active_day', 0)}</b>\n"
        text += f"• За неделю: <b>{metrics.get('active_week', 0)}</b>\n"
        text += f"• За месяц: <b>{metrics.get('active_month', 0)}</b>\n\n"
        
        text += "🆕 <b>Новые пользователи:</b>\n"
        text += f"• За неделю: <b>{metrics.get('new_week', 0)}</b>\n"
        text += f"• За месяц: <b>{metrics.get('new_month', 0)}</b>\n\n"
        
        text += "📚 <b>Топ-5 групп:</b>\n"
        for i, (group, count) in enumerate(metrics.get('top_groups', []), 1):
            text += f"{i}. {group} — <b>{count}</b> чел.\n"
        
        text += f"\n⏰ <b>Средние пропуски:</b> <b>{metrics.get('avg_missed_hours', 0)}</b>ч\n\n"
        
        text += "📉 <b>Группы с наибольшими пропусками:</b>\n"
        for i, (group, hours) in enumerate(metrics.get('top_groups_by_hours', []), 1):
            text += f"{i}. {group} — <b>{hours}</b>ч\n"
        
        return text


# Глобальный экземпляр
_analytics_manager = None


def get_analytics_manager() -> AnalyticsManager:
    """Получить глобальный экземпляр AnalyticsManager"""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager
