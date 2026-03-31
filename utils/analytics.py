"""
Модуль аналитики посещаемости
"""
import io
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Использовать backend без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from utils.db import DB
from utils.log import create_logger

logger = create_logger(__name__)


class Analytics:
    def __init__(self):
        self.db = DB()
        # Настройка шрифтов для поддержки кириллицы
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
    
    async def generate_attendance_chart(self, user_id: int, days: int = 30) -> bytes:
        """
        Генерация графика посещаемости за последние N дней
        Возвращает изображение в формате bytes
        """
        logger.info(f"Генерация графика посещаемости для пользователя {user_id}")
        
        try:
            # Получаем историю пропущенных часов
            history = self.db.get_hours_history(user_id, days)
            
            logger.info(f"Получено записей из БД: {len(history) if history else 0}")
            
            if not history:
                # Если истории нет, создаем пустой график
                logger.warning("История пуста, создаем пустой график")
                return await self._generate_empty_chart()
            
            # Группируем данные по датам и суммируем часы за каждый день
            daily_hours = {}
            for row in history:
                date_str = row[0]
                hours_value = int(row[1])
                
                if date_str not in daily_hours:
                    daily_hours[date_str] = 0
                daily_hours[date_str] += hours_value
            
            logger.info(f"Сгруппировано по датам: {daily_hours}")
            
            # Проверяем, есть ли хоть какие-то данные после группировки
            if not daily_hours:
                logger.warning("После группировки данных нет")
                return await self._generate_empty_chart()
            
            # Сортируем по датам и создаем накопительный итог
            sorted_dates = sorted(daily_hours.keys())
            dates = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]
            
            # Вычисляем накопительный итог
            cumulative_hours = []
            total = 0
            for date_str in sorted_dates:
                total += daily_hours[date_str]
                # Не допускаем отрицательных значений
                cumulative_hours.append(max(0, total))
            
            logger.info(f"Накопительные значения: {cumulative_hours}")
            
            # Проверяем, есть ли хоть одно ненулевое значение
            if all(h == 0 for h in cumulative_hours):
                logger.warning("Все накопительные значения равны 0")
                return await self._generate_empty_chart()
            
            hours = cumulative_hours
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Линейный график
            ax.plot(dates, hours, marker='o', linestyle='-', linewidth=2, 
                   markersize=6, color='#FF6B6B', label='Пропущенные часы')
            
            # Заливка под графиком
            ax.fill_between(dates, hours, alpha=0.3, color='#FF6B6B')
            
            # Настройка осей
            ax.set_xlabel('Дата', fontsize=12, fontweight='bold')
            ax.set_ylabel('Часы', fontsize=12, fontweight='bold')
            ax.set_title(f'График пропущенных часов за последние {days} дней', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Форматирование дат на оси X
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            
            # Определяем интервал в зависимости от количества дней
            if days <= 7:
                interval = 1  # Каждый день
            elif days <= 14:
                interval = 2  # Каждые 2 дня
            elif days <= 30:
                interval = 3  # Каждые 3 дня
            else:
                interval = max(1, days // 10)  # Для больших периодов
            
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
            
            # Если данных мало, показываем все точки
            if len(dates) <= 10:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            plt.xticks(rotation=45, ha='right')
            
            # Сетка
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Легенда
            ax.legend(loc='upper left', fontsize=10)
            
            # Добавление статистики
            total_hours = sum(hours)
            avg_hours = total_hours / len(hours) if hours else 0
            max_hours = max(hours) if hours else 0
            
            stats_text = (
                f'Всего: {total_hours} ч\n'
                f'Среднее: {avg_hours:.1f} ч\n'
                f'Максимум: {max_hours} ч'
            )
            
            ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # Плотная компоновка
            plt.tight_layout()
            
            # Сохранение в bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            logger.info(f"График успешно сгенерирован для пользователя {user_id}")
            return buf.getvalue()
        
        except Exception as e:
            logger.error(f"Ошибка генерации графика для пользователя {user_id}: {e}")
            return await self._generate_error_chart()
    
    async def _generate_empty_chart(self) -> bytes:
        """Генерация пустого графика с сообщением"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'Нет данных для отображения\n\nНачните отмечать пропущенные часы!',
               ha='center', va='center', fontsize=16, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf.getvalue()
    
    async def _generate_error_chart(self) -> bytes:
        """Генерация графика с сообщением об ошибке"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'Ошибка генерации графика\n\nПопробуйте позже',
               ha='center', va='center', fontsize=16, color='red')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf.getvalue()
    
    async def generate_weekly_comparison(self, user_id: int) -> bytes:
        """
        Генерация графика сравнения по неделям
        """
        logger.info(f"Генерация недельного сравнения для пользователя {user_id}")
        
        try:
            # Получаем данные за последние 4 недели
            history = self.db.get_hours_history(user_id, 28)
            
            if not history:
                return await self._generate_empty_chart()
            
            # Сначала группируем по датам
            daily_hours = {}
            for row in history:
                date_str = row[0]
                hours_value = int(row[1])
                
                if date_str not in daily_hours:
                    daily_hours[date_str] = 0
                daily_hours[date_str] += hours_value
            
            # Группировка по неделям
            weeks_data = {}
            for date_str, hours_value in daily_hours.items():
                date = datetime.strptime(date_str, "%Y-%m-%d")
                week_num = date.isocalendar()[1]
                year = date.year
                week_key = f"{year}-W{week_num}"
                
                if week_key not in weeks_data:
                    weeks_data[week_key] = 0
                # Суммируем только положительные значения (добавленные часы)
                if hours_value > 0:
                    weeks_data[week_key] += hours_value
            
            # Сортировка по неделям
            sorted_weeks = sorted(weeks_data.items())
            week_labels = [f"Неделя {i+1}" for i in range(len(sorted_weeks))]
            week_hours = [hours for _, hours in sorted_weeks]
            
            # Создание столбчатого графика
            fig, ax = plt.subplots(figsize=(10, 6))
            
            bars = ax.bar(week_labels, week_hours, color='#4ECDC4', alpha=0.8, edgecolor='black')
            
            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)} ч',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            ax.set_xlabel('Период', fontsize=12, fontweight='bold')
            ax.set_ylabel('Пропущенные часы', fontsize=12, fontweight='bold')
            ax.set_title('Сравнение пропусков по неделям', fontsize=14, fontweight='bold', pad=20)
            
            ax.grid(True, alpha=0.3, axis='y', linestyle='--')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            return buf.getvalue()
        
        except Exception as e:
            logger.error(f"Ошибка генерации недельного сравнения для пользователя {user_id}: {e}")
            return await self._generate_error_chart()
    
    def get_attendance_stats(self, user_id: int, days: int = 30) -> dict:
        """
        Получить статистику посещаемости
        """
        history = self.db.get_hours_history(user_id, days)
        
        if not history:
            return {
                "total_hours": 0,
                "avg_per_day": 0,
                "max_day": 0,
                "days_with_misses": 0,
                "total_days": days
            }
        
        # Группируем данные по датам
        daily_hours = {}
        for row in history:
            date_str = row[0]
            hours_value = int(row[1])
            
            if date_str not in daily_hours:
                daily_hours[date_str] = 0
            daily_hours[date_str] += hours_value
        
        # Вычисляем накопительный итог для получения текущего значения
        total = 0
        for date_str in sorted(daily_hours.keys()):
            total += daily_hours[date_str]
        
        # Считаем только положительные дневные значения для статистики
        positive_days = [h for h in daily_hours.values() if h > 0]
        
        return {
            "total_hours": max(0, total),  # Текущее накопленное значение
            "avg_per_day": sum(positive_days) / len(positive_days) if positive_days else 0,
            "max_day": max(positive_days) if positive_days else 0,
            "days_with_misses": len(positive_days),
            "total_days": days
        }
    
    def get_comparison_with_previous_period(self, user_id: int, days: int = 30) -> dict:
        """
        Сравнение с предыдущим периодом
        """
        # Текущий период
        current_end = datetime.now().strftime("%Y-%m-%d")
        current_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        current_total = self.db.get_total_hours_by_period(user_id, current_start, current_end)
        
        # Предыдущий период
        previous_end = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        previous_start = (datetime.now() - timedelta(days=days*2)).strftime("%Y-%m-%d")
        previous_total = self.db.get_total_hours_by_period(user_id, previous_start, previous_end)
        
        # Вычисление изменения
        if previous_total > 0:
            change_percent = ((current_total - previous_total) / previous_total) * 100
        else:
            change_percent = 0 if current_total == 0 else 100
        
        return {
            "current_period": current_total,
            "previous_period": previous_total,
            "change": current_total - previous_total,
            "change_percent": change_percent,
            "is_improvement": current_total < previous_total
        }


# Глобальный экземпляр
analytics = Analytics()
