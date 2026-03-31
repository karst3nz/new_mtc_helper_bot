"""
Тесты для модуля calendar_keyboard
"""
import pytest
from datetime import datetime
from utils.calendar_keyboard import create_calendar, process_calendar_callback


class TestCreateCalendar:
    """Тесты для функции create_calendar"""
    
    def test_create_calendar_current_month(self):
        """Тест создания календаря для текущего месяца"""
        keyboard = create_calendar()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        
        # Проверяем наличие заголовка с месяцем
        header_row = keyboard.inline_keyboard[0]
        assert len(header_row) == 3
        assert header_row[0].text == "◀️"
        assert header_row[2].text == "▶️"
    
    def test_create_calendar_specific_month(self):
        """Тест создания календаря для конкретного месяца"""
        keyboard = create_calendar(year=2026, month=4)
        
        assert keyboard is not None
        header_row = keyboard.inline_keyboard[0]
        assert "Апрель 2026" in header_row[1].text
    
    def test_create_calendar_january(self):
        """Тест создания календаря для января"""
        keyboard = create_calendar(year=2026, month=1)
        
        assert keyboard is not None
        header_row = keyboard.inline_keyboard[0]
        assert "Январь 2026" in header_row[1].text
    
    def test_create_calendar_december(self):
        """Тест создания календаря для декабря"""
        keyboard = create_calendar(year=2026, month=12)
        
        assert keyboard is not None
        header_row = keyboard.inline_keyboard[0]
        assert "Декабрь 2026" in header_row[1].text
    
    def test_calendar_has_weekdays_row(self):
        """Тест наличия строки с днями недели"""
        keyboard = create_calendar(year=2026, month=4)
        
        # Вторая строка должна содержать дни недели
        weekdays_row = keyboard.inline_keyboard[1]
        assert len(weekdays_row) == 7
        assert weekdays_row[0].text == "Пн"
        assert weekdays_row[6].text == "Вс"
    
    def test_calendar_has_today_button(self):
        """Тест наличия кнопки 'Сегодня'"""
        keyboard = create_calendar()
        
        # Последняя строка должна содержать кнопку "Сегодня"
        last_row = keyboard.inline_keyboard[-1]
        assert len(last_row) >= 1
        assert "Сегодня" in last_row[0].text
    
    def test_calendar_sundays_marked(self):
        """Тест что воскресенья помечены как недоступные"""
        keyboard = create_calendar(year=2026, month=4)
        
        # Проверяем что есть кнопки с 🚫 (воскресенья)
        has_sunday_marker = False
        for row in keyboard.inline_keyboard[2:-1]:  # Пропускаем заголовок, дни недели и последнюю строку
            for button in row:
                if "🚫" in button.text:
                    has_sunday_marker = True
                    assert button.callback_data == "calendar:ignore"
        
        assert has_sunday_marker
    
    def test_calendar_callback_data_format(self):
        """Тест формата callback_data для дней"""
        keyboard = create_calendar(year=2026, month=4)
        
        # Проверяем формат callback_data для обычных дней
        found_valid_day = False
        for row in keyboard.inline_keyboard[2:-1]:
            for button in row:
                if button.text.isdigit():
                    assert button.callback_data.startswith("calendar:select:")
                    parts = button.callback_data.split(":")
                    assert len(parts) == 5
                    assert parts[0] == "calendar"
                    assert parts[1] == "select"
                    found_valid_day = True
        
        assert found_valid_day


class TestProcessCalendarCallback:
    """Тесты для функции process_calendar_callback"""
    
    def test_process_ignore_action(self):
        """Тест обработки действия ignore"""
        result = process_calendar_callback("calendar:ignore")
        
        assert result["action"] == "ignore"
    
    def test_process_prev_month_action(self):
        """Тест обработки перехода к предыдущему месяцу"""
        result = process_calendar_callback("calendar:prev_month:2026:4")
        
        assert result["action"] == "change_month"
        assert result["year"] == 2026
        assert result["month"] == 3
    
    def test_process_prev_month_january(self):
        """Тест перехода с января на декабрь предыдущего года"""
        result = process_calendar_callback("calendar:prev_month:2026:1")
        
        assert result["action"] == "change_month"
        assert result["year"] == 2025
        assert result["month"] == 12
    
    def test_process_next_month_action(self):
        """Тест обработки перехода к следующему месяцу"""
        result = process_calendar_callback("calendar:next_month:2026:4")
        
        assert result["action"] == "change_month"
        assert result["year"] == 2026
        assert result["month"] == 5
    
    def test_process_next_month_december(self):
        """Тест перехода с декабря на январь следующего года"""
        result = process_calendar_callback("calendar:next_month:2026:12")
        
        assert result["action"] == "change_month"
        assert result["year"] == 2027
        assert result["month"] == 1
    
    def test_process_select_action(self):
        """Тест обработки выбора даты"""
        result = process_calendar_callback("calendar:select:2026:4:15")
        
        assert result["action"] == "select"
        assert result["date"] == datetime(2026, 4, 15)
        assert result["date_str"] == "15_04_2026"
    
    def test_process_today_action(self):
        """Тест обработки кнопки 'Сегодня'"""
        result = process_calendar_callback("calendar:today")
        
        assert result["action"] == "select"
        assert result["date"] is not None
        assert isinstance(result["date"], datetime)
        assert result["date_str"] is not None
    
    def test_process_invalid_callback(self):
        """Тест обработки невалидного callback"""
        result = process_calendar_callback("invalid_data")
        
        assert result["action"] == "ignore"
    
    def test_process_empty_callback(self):
        """Тест обработки пустого callback"""
        result = process_calendar_callback("")
        
        assert result["action"] == "ignore"
    
    def test_process_select_first_day_of_month(self):
        """Тест выбора первого дня месяца"""
        result = process_calendar_callback("calendar:select:2026:4:1")
        
        assert result["action"] == "select"
        assert result["date"] == datetime(2026, 4, 1)
        assert result["date_str"] == "01_04_2026"
    
    def test_process_select_last_day_of_month(self):
        """Тест выбора последнего дня месяца"""
        result = process_calendar_callback("calendar:select:2026:4:30")
        
        assert result["action"] == "select"
        assert result["date"] == datetime(2026, 4, 30)
        assert result["date_str"] == "30_04_2026"


class TestCalendarIntegration:
    """Интеграционные тесты календаря"""
    
    def test_calendar_navigation_cycle(self):
        """Тест навигации по месяцам"""
        # Создаем календарь на апрель
        keyboard = create_calendar(year=2026, month=4)
        
        # Получаем callback для следующего месяца
        next_button = keyboard.inline_keyboard[0][2]
        result = process_calendar_callback(next_button.callback_data)
        
        assert result["action"] == "change_month"
        assert result["month"] == 5
        
        # Создаем календарь на май
        keyboard_may = create_calendar(year=result["year"], month=result["month"])
        
        # Возвращаемся назад
        prev_button = keyboard_may.inline_keyboard[0][0]
        result_back = process_calendar_callback(prev_button.callback_data)
        
        assert result_back["action"] == "change_month"
        assert result_back["month"] == 4
    
    def test_calendar_year_boundary(self):
        """Тест перехода через границу года"""
        # Декабрь 2026
        keyboard_dec = create_calendar(year=2026, month=12)
        next_button = keyboard_dec.inline_keyboard[0][2]
        result = process_calendar_callback(next_button.callback_data)
        
        assert result["year"] == 2027
        assert result["month"] == 1
        
        # Январь 2027
        keyboard_jan = create_calendar(year=2027, month=1)
        prev_button = keyboard_jan.inline_keyboard[0][0]
        result_back = process_calendar_callback(prev_button.callback_data)
        
        assert result_back["year"] == 2026
        assert result_back["month"] == 12
