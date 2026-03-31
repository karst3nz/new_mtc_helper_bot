"""
Константы UI для единообразного интерфейса
"""
from aiogram import types


class UIConstants:
    """Стандартные элементы UI"""
    
    # Навигационные кнопки
    BACK = "◀️ Назад"
    BACK_TO_MAIN = "🏠 Главное меню"
    CANCEL = "❌ Отменить"
    CLOSE = "❌ Закрыть"
    
    # Действия
    CONFIRM = "✅ Подтвердить"
    DELETE = "🗑️ Удалить"
    EDIT = "✏️ Изменить"
    ADD = "➕ Добавить"
    RELOAD = "🔄 Обновить"
    
    # Навигация по датам
    PREV_DAY = "◀️"
    NEXT_DAY = "▶️"
    SELECT_DATE = "📅 Выбрать дату"
    TODAY = "📅 Сегодня"
    
    # Специальные
    SKIP = "⏭️ Пропустить"
    RETURN = "◀️ Вернуться"


class ButtonFactory:
    """Фабрика для создания стандартных кнопок"""
    
    @staticmethod
    def back(callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Назад'"""
        return types.InlineKeyboardButton(
            text=UIConstants.BACK,
            callback_data=callback_data
        )
    
    @staticmethod
    def back_to_main() -> types.InlineKeyboardButton:
        """Кнопка 'Главное меню'"""
        return types.InlineKeyboardButton(
            text=UIConstants.BACK_TO_MAIN,
            callback_data="menu:start"
        )
    
    @staticmethod
    def cancel(callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Отменить'"""
        return types.InlineKeyboardButton(
            text=UIConstants.CANCEL,
            callback_data=callback_data
        )
    
    @staticmethod
    def close() -> types.InlineKeyboardButton:
        """Кнопка 'Закрыть'"""
        return types.InlineKeyboardButton(
            text=UIConstants.CLOSE,
            callback_data="delete_msg"
        )
    
    @staticmethod
    def confirm(callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Подтвердить'"""
        return types.InlineKeyboardButton(
            text=UIConstants.CONFIRM,
            callback_data=callback_data
        )
    
    @staticmethod
    def delete(callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Удалить'"""
        return types.InlineKeyboardButton(
            text=UIConstants.DELETE,
            callback_data=callback_data
        )
    
    @staticmethod
    def edit(text: str, callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Изменить'"""
        return types.InlineKeyboardButton(
            text=f"✏️ {text}",
            callback_data=callback_data
        )
    
    @staticmethod
    def reload(callback_data: str) -> types.InlineKeyboardButton:
        """Кнопка 'Обновить'"""
        return types.InlineKeyboardButton(
            text=UIConstants.RELOAD,
            callback_data=callback_data
        )
