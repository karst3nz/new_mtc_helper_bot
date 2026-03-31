"""
Тесты для модуля ui_constants
"""
import pytest
from utils.ui_constants import ButtonFactory


class TestButtonFactory:
    """Тесты фабрики кнопок"""
    
    def test_button_factory_exists(self):
        """Тест существования фабрики"""
        assert ButtonFactory is not None
        
    def test_create_back_button(self):
        """Тест создания кнопки назад"""
        button = ButtonFactory.back("menu:main")
        assert button is not None
        assert "Назад" in button.text or "◀️" in button.text
        
    def test_create_close_button(self):
        """Тест создания кнопки закрыть"""
        button = ButtonFactory.close()
        assert button is not None
        assert "Закрыть" in button.text or "❌" in button.text
        
    def test_create_cancel_button(self):
        """Тест создания кнопки отмена"""
        button = ButtonFactory.cancel("menu:main")
        assert button is not None
        assert "Отмена" in button.text or "❌" in button.text


class TestButtonText:
    """Тесты текста кнопок"""
    
    def test_back_button_text(self):
        """Тест текста кнопки назад"""
        button = ButtonFactory.back("test")
        assert len(button.text) > 0
        
    def test_close_button_text(self):
        """Тест текста кнопки закрыть"""
        button = ButtonFactory.close()
        assert len(button.text) > 0
        
    def test_cancel_button_text(self):
        """Тест текста кнопки отмена"""
        button = ButtonFactory.cancel("test")
        assert len(button.text) > 0


class TestButtonCallbackData:
    """Тесты callback data кнопок"""
    
    def test_back_button_callback(self):
        """Тест callback data кнопки назад"""
        button = ButtonFactory.back("menu:settings")
        assert button.callback_data is not None
        assert "menu:settings" in button.callback_data
        
    def test_close_button_callback(self):
        """Тест callback data кнопки закрыть"""
        button = ButtonFactory.close()
        assert button.callback_data is not None
        
    def test_cancel_button_callback(self):
        """Тест callback data кнопки отмена"""
        button = ButtonFactory.cancel("menu:main")
        assert button.callback_data is not None


class TestButtonTypes:
    """Тесты типов кнопок"""
    
    def test_button_is_inline_keyboard_button(self):
        """Тест что кнопка - InlineKeyboardButton"""
        from aiogram.types import InlineKeyboardButton
        button = ButtonFactory.back("test")
        assert isinstance(button, InlineKeyboardButton)
        
    def test_multiple_buttons_same_type(self):
        """Тест что все кнопки одного типа"""
        from aiogram.types import InlineKeyboardButton
        buttons = [
            ButtonFactory.back("test"),
            ButtonFactory.close(),
            ButtonFactory.cancel("test")
        ]
        assert all(isinstance(b, InlineKeyboardButton) for b in buttons)


class TestButtonEdgeCases:
    """Тесты граничных случаев"""
    
    def test_back_button_empty_callback(self):
        """Тест кнопки назад с пустым callback"""
        button = ButtonFactory.back("")
        assert button is not None
        
    def test_cancel_button_empty_callback(self):
        """Тест кнопки отмена с пустым callback"""
        button = ButtonFactory.cancel("")
        assert button is not None
        
    def test_button_with_long_callback(self):
        """Тест кнопки с длинным callback"""
        long_callback = "menu:" + "a" * 50
        button = ButtonFactory.back(long_callback)
        assert button is not None


class TestButtonConsistency:
    """Тесты консистентности кнопок"""
    
    def test_same_input_same_button(self):
        """Тест что одинаковый вход дает одинаковую кнопку"""
        button1 = ButtonFactory.back("menu:main")
        button2 = ButtonFactory.back("menu:main")
        assert button1.text == button2.text
        assert button1.callback_data == button2.callback_data
        
    def test_different_input_different_button(self):
        """Тест что разный вход дает разные кнопки"""
        button1 = ButtonFactory.back("menu:main")
        button2 = ButtonFactory.back("menu:settings")
        assert button1.callback_data != button2.callback_data


class TestButtonIntegration:
    """Интеграционные тесты кнопок"""
    
    def test_create_button_row(self):
        """Тест создания ряда кнопок"""
        buttons = [
            ButtonFactory.back("menu:main"),
            ButtonFactory.close()
        ]
        assert len(buttons) == 2
        
    def test_create_button_grid(self):
        """Тест создания сетки кнопок"""
        grid = [
            [ButtonFactory.back("menu:main")],
            [ButtonFactory.close()]
        ]
        assert len(grid) == 2
        assert len(grid[0]) == 1


class TestButtonAttributes:
    """Тесты атрибутов кнопок"""
    
    def test_button_has_text(self):
        """Тест наличия текста"""
        button = ButtonFactory.back("test")
        assert hasattr(button, 'text')
        
    def test_button_has_callback_data(self):
        """Тест наличия callback_data"""
        button = ButtonFactory.back("test")
        assert hasattr(button, 'callback_data')
        
    def test_button_no_url(self):
        """Тест отсутствия URL"""
        button = ButtonFactory.back("test")
        assert button.url is None


class TestButtonReliability:
    """Тесты надежности кнопок"""
    
    def test_create_100_buttons(self):
        """Тест создания 100 кнопок"""
        buttons = [ButtonFactory.back(f"menu:{i}") for i in range(100)]
        assert len(buttons) == 100
        
    def test_buttons_unique_callbacks(self):
        """Тест уникальности callback"""
        buttons = [ButtonFactory.back(f"menu:{i}") for i in range(10)]
        callbacks = [b.callback_data for b in buttons]
        assert len(set(callbacks)) == 10
        
    def test_button_text_not_empty(self):
        """Тест что текст кнопки не пустой"""
        button = ButtonFactory.back("test")
        assert len(button.text) > 0
        
    def test_button_callback_not_empty(self):
        """Тест что callback не пустой"""
        button = ButtonFactory.back("test")
        assert len(button.callback_data) > 0
        
    def test_close_button_always_same(self):
        """Тест что кнопка закрыть всегда одинаковая"""
        button1 = ButtonFactory.close()
        button2 = ButtonFactory.close()
        assert button1.text == button2.text
        
    def test_button_factory_performance(self):
        """Тест производительности фабрики"""
        import time
        start = time.time()
        for _ in range(1000):
            ButtonFactory.back("test")
        duration = time.time() - start
        assert duration < 1.0
        
    def test_button_with_unicode(self):
        """Тест кнопки с unicode"""
        button = ButtonFactory.back("menu:настройки")
        assert button is not None
        assert button.callback_data is not None
