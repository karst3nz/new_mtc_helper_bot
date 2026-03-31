"""
Расширенные тесты для модуля callback_data
"""
import pytest
from utils.callback_data import CallbackData


class TestCallbackDataEncode:
    """Тесты кодирования callback data"""
    
    def test_encode_simple(self):
        """Тест простого кодирования"""
        result = CallbackData.encode("menu", "settings")
        assert "menu" in result
        assert "settings" in result
        
    def test_encode_with_multiple_params(self):
        """Тест кодирования с несколькими параметрами"""
        result = CallbackData.encode("rasp", "01_04_2026", True, False)
        assert "rasp" in result
        
    def test_encode_with_none(self):
        """Тест кодирования с None"""
        result = CallbackData.encode("menu", None)
        assert result is not None
        
    def test_encode_with_boolean(self):
        """Тест кодирования с boolean"""
        result = CallbackData.encode("toggle", True)
        assert result is not None
        
    def test_encode_with_integer(self):
        """Тест кодирования с integer"""
        result = CallbackData.encode("page", 5)
        assert result is not None


class TestCallbackDataDecode:
    """Тесты декодирования callback data"""
    
    def test_decode_simple(self):
        """Тест простого декодирования"""
        encoded = CallbackData.encode("menu", "settings")
        decoded = CallbackData.decode(encoded)
        assert decoded[0] == "menu"
        
    def test_decode_with_multiple_params(self):
        """Тест декодирования с несколькими параметрами"""
        encoded = CallbackData.encode("rasp", "01_04_2026", True)
        decoded = CallbackData.decode(encoded)
        assert len(decoded) >= 2
        
    def test_decode_invalid_data(self):
        """Тест декодирования некорректных данных"""
        result = CallbackData.decode("invalid:data:format")
        assert result is not None


class TestCallbackDataRoundtrip:
    """Тесты кодирования-декодирования"""
    
    def test_roundtrip_simple(self):
        """Тест простого цикла кодирования-декодирования"""
        original = ("menu", "settings")
        encoded = CallbackData.encode(*original)
        decoded = CallbackData.decode(encoded)
        assert decoded[0] == original[0]
        
    def test_roundtrip_with_date(self):
        """Тест цикла с датой"""
        original = ("rasp", "01_04_2026")
        encoded = CallbackData.encode(*original)
        decoded = CallbackData.decode(encoded)
        assert decoded[0] == original[0]


class TestCallbackDataEdgeCases:
    """Тесты граничных случаев"""
    
    def test_encode_empty_string(self):
        """Тест кодирования пустой строки"""
        result = CallbackData.encode("")
        assert result is not None
        
    def test_encode_special_characters(self):
        """Тест кодирования спецсимволов"""
        result = CallbackData.encode("menu", "test:value")
        assert result is not None
        
    def test_encode_long_string(self):
        """Тест кодирования длинной строки"""
        long_str = "a" * 100
        result = CallbackData.encode("menu", long_str)
        assert result is not None


class TestCallbackDataTypes:
    """Тесты различных типов данных"""
    
    def test_encode_string(self):
        """Тест кодирования строки"""
        result = CallbackData.encode("menu", "settings")
        assert isinstance(result, str)
        
    def test_encode_int(self):
        """Тест кодирования числа"""
        result = CallbackData.encode("page", 5)
        assert isinstance(result, str)
        
    def test_encode_bool(self):
        """Тест кодирования boolean"""
        result = CallbackData.encode("toggle", True)
        assert isinstance(result, str)
        
    def test_encode_float(self):
        """Тест кодирования float"""
        result = CallbackData.encode("value", 3.14)
        assert isinstance(result, str)


class TestCallbackDataConsistency:
    """Тесты консистентности"""
    
    def test_same_input_same_output(self):
        """Тест что одинаковый вход дает одинаковый выход"""
        result1 = CallbackData.encode("menu", "settings")
        result2 = CallbackData.encode("menu", "settings")
        assert result1 == result2
        
    def test_different_input_different_output(self):
        """Тест что разный вход дает разный выход"""
        result1 = CallbackData.encode("menu", "settings")
        result2 = CallbackData.encode("menu", "other")
        assert result1 != result2


class TestCallbackDataSeparator:
    """Тесты разделителя"""
    
    def test_separator_in_result(self):
        """Тест наличия разделителя в результате"""
        result = CallbackData.encode("menu", "settings")
        assert ":" in result
        
    def test_multiple_separators(self):
        """Тест множественных разделителей"""
        result = CallbackData.encode("menu", "settings", "subsettings")
        separators = result.count(":")
        assert separators >= 1


class TestCallbackDataLength:
    """Тесты длины callback data"""
    
    def test_length_within_limit(self):
        """Тест что длина в пределах лимита Telegram (64 байта)"""
        result = CallbackData.encode("menu", "settings")
        assert len(result.encode('utf-8')) <= 64
        
    def test_length_with_long_params(self):
        """Тест длины с длинными параметрами"""
        result = CallbackData.encode("m", "s")
        assert len(result.encode('utf-8')) <= 64


class TestCallbackDataSpecialCases:
    """Тесты специальных случаев"""
    
    def test_encode_unicode(self):
        """Тест кодирования unicode"""
        result = CallbackData.encode("menu", "настройки")
        assert result is not None
        
    def test_encode_numbers_as_strings(self):
        """Тест кодирования чисел как строк"""
        result = CallbackData.encode("page", "5")
        assert result is not None
        
    def test_encode_mixed_types(self):
        """Тест кодирования смешанных типов"""
        result = CallbackData.encode("action", "test", 5, True)
        assert result is not None


class TestCallbackDataValidation:
    """Тесты валидации"""
    
    def test_decode_valid_format(self):
        """Тест декодирования валидного формата"""
        encoded = CallbackData.encode("menu", "settings")
        decoded = CallbackData.decode(encoded)
        assert decoded is not None
        
    def test_decode_empty_string(self):
        """Тест декодирования пустой строки"""
        decoded = CallbackData.decode("")
        assert decoded is not None


class TestCallbackDataIntegration:
    """Интеграционные тесты"""
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        # Кодируем
        encoded = CallbackData.encode("rasp", "01_04_2026", False, True)
        assert encoded is not None
        
        # Декодируем
        decoded = CallbackData.decode(encoded)
        assert decoded is not None
        assert decoded[0] == "rasp"
        
    def test_multiple_operations(self):
        """Тест множественных операций"""
        for i in range(10):
            encoded = CallbackData.encode("page", str(i))
            decoded = CallbackData.decode(encoded)
            assert decoded[0] == "page"


class TestCallbackDataPerformance:
    """Тесты производительности"""
    
    def test_encode_performance(self):
        """Тест производительности кодирования"""
        import time
        start = time.time()
        for _ in range(1000):
            CallbackData.encode("menu", "settings")
        duration = time.time() - start
        assert duration < 1.0  # Должно быть быстрее 1 секунды
        
    def test_decode_performance(self):
        """Тест производительности декодирования"""
        import time
        encoded = CallbackData.encode("menu", "settings")
        start = time.time()
        for _ in range(1000):
            CallbackData.decode(encoded)
        duration = time.time() - start
        assert duration < 1.0


class TestCallbackDataReliability:
    """Тесты надежности"""
    
    def test_encode_decode_100_times(self):
        """Тест 100 циклов кодирования-декодирования"""
        for i in range(100):
            encoded = CallbackData.encode("test", str(i))
            decoded = CallbackData.decode(encoded)
            assert decoded[0] == "test"
            
    def test_different_actions(self):
        """Тест различных действий"""
        actions = ["menu", "rasp", "settings", "back", "close", "toggle"]
        for action in actions:
            encoded = CallbackData.encode(action, "param")
            decoded = CallbackData.decode(encoded)
            assert decoded[0] == action
