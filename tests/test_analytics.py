"""
Тесты для модуля analytics
"""
import pytest
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image
from utils.analytics import Analytics


@pytest.fixture
def mock_db():
    """Мок базы данных"""
    db = Mock()
    db.get_hours_history = Mock()
    db.get_total_hours_by_period = Mock()
    return db


@pytest.fixture
def analytics_instance(mock_db):
    """Экземпляр Analytics с моком БД"""
    with patch('utils.analytics.DB', return_value=mock_db):
        analytics = Analytics()
        analytics.db = mock_db
        return analytics


@pytest.fixture
def sample_hours_history():
    """Примерная история пропущенных часов"""
    base_date = datetime.now() - timedelta(days=10)
    return [
        ((base_date + timedelta(days=i)).strftime("%Y-%m-%d"), (i % 5) + 1)
        for i in range(10)
    ]


@pytest.fixture
def empty_hours_history():
    """Пустая история"""
    return []


class TestAnalyticsChartGeneration:
    """Тесты генерации графиков"""
    
    @pytest.mark.asyncio
    async def test_generate_attendance_chart_success(self, analytics_instance, sample_hours_history):
        """Тест успешной генерации графика посещаемости"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        
        # Проверяем что это валидное изображение
        img = Image.open(io.BytesIO(chart_bytes))
        assert img.format == 'PNG'
        assert img.size[0] > 0
        assert img.size[1] > 0
    
    @pytest.mark.asyncio
    async def test_generate_attendance_chart_empty_data(self, analytics_instance, empty_hours_history):
        """Тест генерации графика с пустыми данными"""
        analytics_instance.db.get_hours_history.return_value = empty_hours_history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        
        # Проверяем что это валидное изображение
        img = Image.open(io.BytesIO(chart_bytes))
        assert img.format == 'PNG'
    
    @pytest.mark.asyncio
    async def test_generate_attendance_chart_different_periods(self, analytics_instance, sample_hours_history):
        """Тест генерации графиков для разных периодов"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        for days in [7, 14, 30, 60]:
            chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=days)
            
            assert chart_bytes is not None
            assert len(chart_bytes) > 0
    
    @pytest.mark.asyncio
    async def test_generate_attendance_chart_db_error(self, analytics_instance):
        """Тест обработки ошибки БД"""
        analytics_instance.db.get_hours_history.side_effect = Exception("Database error")
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        # Должен вернуть график с ошибкой
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
    
    @pytest.mark.asyncio
    async def test_generate_weekly_comparison_success(self, analytics_instance):
        """Тест генерации недельного сравнения"""
        # Создаем данные за 4 недели
        history = []
        base_date = datetime.now() - timedelta(days=28)
        for i in range(28):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            hours = (i % 7) + 1
            history.append((date, hours))
        
        analytics_instance.db.get_hours_history.return_value = history
        
        chart_bytes = await analytics_instance.generate_weekly_comparison(12345)
        
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        
        # Проверяем что это валидное изображение
        img = Image.open(io.BytesIO(chart_bytes))
        assert img.format == 'PNG'
    
    @pytest.mark.asyncio
    async def test_generate_weekly_comparison_empty_data(self, analytics_instance, empty_hours_history):
        """Тест недельного сравнения с пустыми данными"""
        analytics_instance.db.get_hours_history.return_value = empty_hours_history
        
        chart_bytes = await analytics_instance.generate_weekly_comparison(12345)
        
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
    
    @pytest.mark.asyncio
    async def test_generate_weekly_comparison_db_error(self, analytics_instance):
        """Тест обработки ошибки БД при недельном сравнении"""
        analytics_instance.db.get_hours_history.side_effect = Exception("Database error")
        
        chart_bytes = await analytics_instance.generate_weekly_comparison(12345)
        
        # Должен вернуть график с ошибкой
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)


class TestAnalyticsStatistics:
    """Тесты статистики"""
    
    def test_get_attendance_stats_with_data(self, analytics_instance, sample_hours_history):
        """Тест получения статистики с данными"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        
        assert stats is not None
        assert 'total_hours' in stats
        assert 'avg_per_day' in stats
        assert 'max_day' in stats
        assert 'days_with_misses' in stats
        assert 'total_days' in stats
        
        assert stats['total_hours'] > 0
        assert stats['avg_per_day'] > 0
        assert stats['max_day'] > 0
        assert stats['total_days'] == 30
    
    def test_get_attendance_stats_empty_data(self, analytics_instance, empty_hours_history):
        """Тест получения статистики без данных"""
        analytics_instance.db.get_hours_history.return_value = empty_hours_history
        
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        
        assert stats is not None
        assert stats['total_hours'] == 0
        assert stats['avg_per_day'] == 0
        assert stats['max_day'] == 0
        assert stats['days_with_misses'] == 0
        assert stats['total_days'] == 30
    
    def test_get_attendance_stats_calculation(self, analytics_instance):
        """Тест правильности расчетов статистики"""
        history = [
            ('2026-03-25', 2),
            ('2026-03-26', 4),
            ('2026-03-27', 0),
            ('2026-03-28', 6),
            ('2026-03-29', 2),
        ]
        analytics_instance.db.get_hours_history.return_value = history
        
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        
        assert stats['total_hours'] == 14  # 2+4+0+6+2
        # avg_per_day считается только по дням с пропусками > 0
        assert stats['avg_per_day'] == 14 / 4  # 3.5 (только 4 дня с пропусками)
        assert stats['max_day'] == 6
        assert stats['days_with_misses'] == 4  # Дни с пропусками > 0
    
    def test_get_attendance_stats_different_periods(self, analytics_instance, sample_hours_history):
        """Тест статистики для разных периодов"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        for days in [7, 14, 30, 60]:
            stats = analytics_instance.get_attendance_stats(12345, days=days)
            
            assert stats['total_days'] == days


class TestAnalyticsComparison:
    """Тесты сравнения периодов"""
    
    def test_get_comparison_with_previous_period_improvement(self, analytics_instance):
        """Тест сравнения с улучшением"""
        analytics_instance.db.get_total_hours_by_period.side_effect = [10, 20]  # current, previous
        
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        
        assert comparison is not None
        assert comparison['current_period'] == 10
        assert comparison['previous_period'] == 20
        assert comparison['change'] == -10
        assert comparison['change_percent'] == -50.0
        assert comparison['is_improvement'] is True
    
    def test_get_comparison_with_previous_period_worsening(self, analytics_instance):
        """Тест сравнения с ухудшением"""
        analytics_instance.db.get_total_hours_by_period.side_effect = [30, 20]  # current, previous
        
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        
        assert comparison is not None
        assert comparison['current_period'] == 30
        assert comparison['previous_period'] == 20
        assert comparison['change'] == 10
        assert comparison['change_percent'] == 50.0
        assert comparison['is_improvement'] is False
    
    def test_get_comparison_with_previous_period_no_change(self, analytics_instance):
        """Тест сравнения без изменений"""
        analytics_instance.db.get_total_hours_by_period.side_effect = [15, 15]  # current, previous
        
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        
        assert comparison is not None
        assert comparison['current_period'] == 15
        assert comparison['previous_period'] == 15
        assert comparison['change'] == 0
        assert comparison['change_percent'] == 0.0
        assert comparison['is_improvement'] is False
    
    def test_get_comparison_with_previous_period_zero_previous(self, analytics_instance):
        """Тест сравнения когда предыдущий период = 0"""
        analytics_instance.db.get_total_hours_by_period.side_effect = [10, 0]  # current, previous
        
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        
        assert comparison is not None
        assert comparison['current_period'] == 10
        assert comparison['previous_period'] == 0
        assert comparison['change'] == 10
        assert comparison['change_percent'] == 100.0
        assert comparison['is_improvement'] is False
    
    def test_get_comparison_with_previous_period_both_zero(self, analytics_instance):
        """Тест сравнения когда оба периода = 0"""
        analytics_instance.db.get_total_hours_by_period.side_effect = [0, 0]  # current, previous
        
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        
        assert comparison is not None
        assert comparison['current_period'] == 0
        assert comparison['previous_period'] == 0
        assert comparison['change'] == 0
        assert comparison['change_percent'] == 0.0
        assert comparison['is_improvement'] is False


class TestAnalyticsImageValidation:
    """Тесты валидации изображений"""
    
    @pytest.mark.asyncio
    async def test_chart_is_valid_png(self, analytics_instance, sample_hours_history):
        """Тест что график - валидный PNG"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        # Проверяем PNG сигнатуру
        assert chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    @pytest.mark.asyncio
    async def test_chart_has_reasonable_size(self, analytics_instance, sample_hours_history):
        """Тест что размер графика разумный"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        # Размер должен быть больше 1KB и меньше 5MB
        assert len(chart_bytes) > 1024
        assert len(chart_bytes) < 5 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_chart_dimensions(self, analytics_instance, sample_hours_history):
        """Тест размеров графика"""
        analytics_instance.db.get_hours_history.return_value = sample_hours_history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        img = Image.open(io.BytesIO(chart_bytes))
        width, height = img.size
        
        # Проверяем что размеры соответствуют ожидаемым (figsize=(10, 6) с dpi=100)
        assert width > 500  # Примерно 1000 пикселей
        assert height > 300  # Примерно 600 пикселей


class TestAnalyticsEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_single_data_point(self, analytics_instance):
        """Тест с одной точкой данных"""
        history = [('2026-03-31', 5)]
        analytics_instance.db.get_hours_history.return_value = history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0
    
    @pytest.mark.asyncio
    async def test_all_zero_hours(self, analytics_instance):
        """Тест когда все часы = 0"""
        history = [(f'2026-03-{i:02d}', 0) for i in range(1, 11)]
        analytics_instance.db.get_hours_history.return_value = history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        assert chart_bytes is not None
        
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        assert stats['total_hours'] == 0
        assert stats['days_with_misses'] == 0
    
    @pytest.mark.asyncio
    async def test_very_large_hours(self, analytics_instance):
        """Тест с очень большими значениями часов"""
        history = [('2026-03-31', 1000)]
        analytics_instance.db.get_hours_history.return_value = history
        
        chart_bytes = await analytics_instance.generate_attendance_chart(12345, days=30)
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0
    
    def test_stats_with_mixed_data(self, analytics_instance):
        """Тест статистики со смешанными данными"""
        history = [
            ('2026-03-25', 0),
            ('2026-03-26', 10),
            ('2026-03-27', 0),
            ('2026-03-28', 5),
            ('2026-03-29', 0),
        ]
        analytics_instance.db.get_hours_history.return_value = history
        
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        
        assert stats['total_hours'] == 15
        assert stats['days_with_misses'] == 2  # Только дни с hours > 0
        assert stats['max_day'] == 10


class TestAnalyticsIntegration:
    """Интеграционные тесты"""
    
    @pytest.mark.asyncio
    async def test_full_analytics_workflow(self, analytics_instance):
        """Тест полного цикла аналитики"""
        # Подготовка данных
        history = [
            ((datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), (i % 5) + 1)
            for i in range(30)
        ]
        analytics_instance.db.get_hours_history.return_value = history
        analytics_instance.db.get_total_hours_by_period.side_effect = [50, 60]
        
        # Генерация графика
        chart = await analytics_instance.generate_attendance_chart(12345, days=30)
        assert chart is not None
        
        # Получение статистики
        stats = analytics_instance.get_attendance_stats(12345, days=30)
        assert stats['total_hours'] > 0
        
        # Сравнение периодов
        comparison = analytics_instance.get_comparison_with_previous_period(12345, days=30)
        assert comparison['is_improvement'] is True
        
        # Недельное сравнение
        weekly = await analytics_instance.generate_weekly_comparison(12345)
        assert weekly is not None
