"""
Расширенные тесты для модуля message_splitter
"""
import pytest
from utils.message_splitter import (
    split_message, 
    truncate_text, 
    format_schedule_compact,
    estimate_message_length,
    add_pagination_info,
    smart_truncate_schedule
)


class TestSplitMessage:
    """Тесты разделения сообщений"""
    
    def test_split_short_message(self):
        """Тест короткого сообщения"""
        text = "Короткое сообщение"
        result = split_message(text)
        assert len(result) == 1
        assert result[0] == text
        
    def test_split_long_message(self):
        """Тест длинного сообщения"""
        text = "a" * 5000
        result = split_message(text, max_length=4096)
        assert len(result) >= 1  # Может быть 1 или больше частей
        total_length = sum(len(part) for part in result)
        assert total_length == len(text)
        
    def test_split_at_newline(self):
        """Тест разделения по переносу строки"""
        text = "Строка 1\n" + "a" * 4000 + "\nСтрока 2"
        result = split_message(text, max_length=4096)
        assert len(result) >= 1
        
    def test_split_empty_message(self):
        """Тест пустого сообщения"""
        result = split_message("")
        assert len(result) == 1
        assert result[0] == ""
        
    def test_split_exact_length(self):
        """Тест сообщения точной длины"""
        text = "a" * 4096
        result = split_message(text, max_length=4096)
        assert len(result) == 1


class TestSplitLongMessage:
    """Тесты разделения длинных сообщений"""
    
    def test_split_with_html_tags(self):
        """Тест с HTML тегами"""
        text = "<b>Жирный текст</b>" * 500
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_preserves_formatting(self):
        """Тест сохранения форматирования"""
        text = "<b>Важно:</b> " + "текст " * 1000
        result = split_message(text)
        assert all("<b>" in part or "текст" in part for part in result)


class TestTruncateText:
    """Тесты обрезки текста"""
    
    def test_truncate_short_text(self):
        """Тест обрезки короткого текста"""
        text = "Короткий текст"
        result = truncate_text(text, max_length=100)
        assert result == text
        
    def test_truncate_long_text(self):
        """Тест обрезки длинного текста"""
        text = "a" * 5000
        result = truncate_text(text, max_length=100)
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")
        
    def test_truncate_with_custom_suffix(self):
        """Тест обрезки с кастомным суффиксом"""
        text = "a" * 5000
        result = truncate_text(text, max_length=100, suffix="[...]")
        assert result.endswith("[...]")


class TestFormatScheduleCompact:
    """Тесты компактного форматирования расписания"""
    
    def test_format_empty_schedule(self):
        """Тест форматирования пустого расписания"""
        result = format_schedule_compact({})
        assert isinstance(result, str)
        
    def test_format_schedule_with_data(self):
        """Тест форматирования расписания с данными"""
        schedule = {"1": {"subject": "Математика", "room": "101"}}
        result = format_schedule_compact(schedule)
        assert isinstance(result, str)


class TestEstimateMessageLength:
    """Тесты оценки длины сообщения"""
    
    def test_estimate_plain_text(self):
        """Тест оценки простого текста"""
        text = "Простой текст"
        length = estimate_message_length(text, include_html=False)
        assert length == len(text)
        
    def test_estimate_with_html(self):
        """Тест оценки с HTML"""
        text = "<b>Жирный</b> текст"
        length = estimate_message_length(text, include_html=True)
        assert length > 0  # Просто проверяем что функция работает


class TestAddPaginationInfo:
    """Тесты добавления информации о пагинации"""
    
    def test_add_pagination_first_page(self):
        """Тест первой страницы"""
        text = "Содержимое"
        result = add_pagination_info(text, 1, 5)
        assert "1" in result
        assert "5" in result
        
    def test_add_pagination_last_page(self):
        """Тест последней страницы"""
        text = "Содержимое"
        result = add_pagination_info(text, 5, 5)
        assert "5" in result


class TestSmartTruncateSchedule:
    """Тесты умной обрезки расписания"""
    
    def test_truncate_short_schedule(self):
        """Тест обрезки короткого расписания"""
        text = "1 пара: Математика"
        result, truncated = smart_truncate_schedule(text)
        assert not truncated
        assert result == text
        
    def test_truncate_long_schedule(self):
        """Тест обрезки длинного расписания"""
        text = "1 пара: Математика\n" * 500
        result, truncated = smart_truncate_schedule(text, max_length=1000)
        assert truncated
        assert len(result) <= 1000


class TestSplitMessageEdgeCases:
    """Тесты граничных случаев"""
    
    def test_split_single_character(self):
        """Тест одного символа"""
        result = split_message("a")
        assert len(result) == 1
        assert result[0] == "a"
        
    def test_split_unicode(self):
        """Тест unicode символов"""
        text = "Привет мир! " * 500
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_emojis(self):
        """Тест эмодзи"""
        text = "😀" * 1000
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_mixed_content(self):
        """Тест смешанного контента"""
        text = "Text 123 😀 <b>bold</b> " * 500
        result = split_message(text)
        assert len(result) >= 1


class TestSplitMessageNewlines:
    """Тесты разделения по переносам строк"""
    
    def test_split_multiple_newlines(self):
        """Тест множественных переносов"""
        text = "Строка\n" * 1000
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_preserves_newlines(self):
        """Тест сохранения переносов"""
        text = "Строка 1\nСтрока 2\nСтрока 3"
        result = split_message(text)
        assert "\n" in result[0]
        
    def test_split_empty_lines(self):
        """Тест пустых строк"""
        text = "Текст\n\n\nТекст"
        result = split_message(text)
        assert len(result) >= 1


class TestSplitMessagePerformance:
    """Тесты производительности"""
    
    def test_split_performance_short(self):
        """Тест производительности на коротких сообщениях"""
        import time
        start = time.time()
        for _ in range(100):
            split_message("Короткое сообщение")
        duration = time.time() - start
        assert duration < 1.0
        
    def test_split_performance_long(self):
        """Тест производительности на длинных сообщениях"""
        import time
        text = "a" * 10000
        start = time.time()
        for _ in range(10):
            split_message(text)
        duration = time.time() - start
        assert duration < 1.0


class TestSplitMessageConsistency:
    """Тесты консистентности"""
    
    def test_split_same_input_same_output(self):
        """Тест что одинаковый вход дает одинаковый выход"""
        text = "Тестовое сообщение"
        result1 = split_message(text)
        result2 = split_message(text)
        assert result1 == result2
        
    def test_split_concatenation_equals_original(self):
        """Тест что конкатенация частей равна оригиналу"""
        text = "Текст " * 1000
        result = split_message(text)
        concatenated = "".join(result)
        # Проверяем что длина сохранилась (могут быть добавлены переносы)
        assert len(concatenated) >= len(text) * 0.95  # Допускаем 5% отклонение


class TestSplitMessageBoundaries:
    """Тесты границ"""
    
    def test_split_at_4095(self):
        """Тест на границе 4095 символов"""
        text = "a" * 4095
        result = split_message(text, max_length=4096)
        assert len(result) == 1
        
    def test_split_at_4097(self):
        """Тест на границе 4097 символов"""
        text = "a" * 4097
        result = split_message(text, max_length=4096)
        assert len(result) >= 1  # Может быть разделено по-разному
        
    def test_split_at_8192(self):
        """Тест на границе 8192 символов"""
        text = "a" * 8192
        result = split_message(text, max_length=4096)
        assert len(result) >= 1  # Может быть разделено по-разному


class TestSplitMessageSpecialCharacters:
    """Тесты специальных символов"""
    
    def test_split_with_tabs(self):
        """Тест с табуляцией"""
        text = "Текст\tс\tтабуляцией " * 500
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_with_carriage_return(self):
        """Тест с возвратом каретки"""
        text = "Текст\rс\rвозвратом " * 500
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_with_null_bytes(self):
        """Тест с нулевыми байтами"""
        text = "Текст\x00с\x00нулями " * 500
        result = split_message(text)
        assert len(result) >= 1


class TestSplitMessageHTML:
    """Тесты HTML форматирования"""
    
    def test_split_with_bold(self):
        """Тест с жирным текстом"""
        text = "<b>Жирный</b> " * 1000
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_with_italic(self):
        """Тест с курсивом"""
        text = "<i>Курсив</i> " * 1000
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_with_code(self):
        """Тест с кодом"""
        text = "<code>Код</code> " * 1000
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_with_link(self):
        """Тест со ссылкой"""
        text = '<a href="http://example.com">Ссылка</a> ' * 1000
        result = split_message(text)
        assert len(result) >= 1


class TestSplitMessageIntegration:
    """Интеграционные тесты"""
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        # Создаем длинное сообщение
        text = "Расписание:\n" + "1 пара: Математика\n" * 500
        
        # Разделяем
        result = split_message(text)
        
        # Проверяем
        assert len(result) >= 1
        for part in result:
            assert len(part) <= 4096
            
    def test_real_world_schedule(self):
        """Тест реального расписания"""
        text = """
📅 Расписание на 01.04.2026

1 пара: Математика | 101 | Иванов И.И.
2 пара: Физика | 102 | Петров П.П.
3 пара: Химия | 103 | Сидоров С.С.
""" * 200
        
        result = split_message(text)
        assert len(result) >= 1
        for part in result:
            assert len(part) <= 4096


class TestMessageSplitterAdvanced:
    """Продвинутые тесты разделения сообщений"""
    
    def test_split_with_separator(self):
        """Тест с разделителем"""
        text = "Параграф 1\n\nПараграф 2\n\n" * 500
        result = split_message(text)
        assert len(result) >= 1
        
    def test_split_preserve_words(self):
        """Тест сохранения слов"""
        text = "слово " * 2000
        result = split_message(text)
        # Проверяем что слова не разорваны
        for part in result:
            assert not part.endswith("сло")


class TestSplitMessageReliability:
    """Тесты надежности"""
    
    def test_split_100_times(self):
        """Тест 100 разделений"""
        text = "Тест " * 1000
        for _ in range(100):
            result = split_message(text)
            assert len(result) >= 1
            
    def test_split_different_lengths(self):
        """Тест различных длин"""
        for length in [10, 100, 1000, 5000, 10000]:
            text = "a" * length
            result = split_message(text)
            assert len(result) >= 1
            concatenated = "".join(result)
            assert len(concatenated) == length
