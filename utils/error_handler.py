"""
Улучшенная обработка ошибок с конкретными решениями для пользователей
"""
from aiogram import types
from utils.ui_constants import ButtonFactory


class ErrorHandler:
    """Класс для создания понятных сообщений об ошибках с решениями"""
    
    @staticmethod
    def group_not_found(group: str, back_callback: str = "menu:settings") -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка: группа не найдена"""
        text = (
            f"❌ <b>Группа {group} не найдена</b>\n\n"
            f"💡 <b>Возможные причины:</b>\n"
            f"  • Неправильный формат номера группы\n"
            f"  • Группа не существует в системе\n"
            f"  • Опечатка в номере\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Проверьте правильность номера группы\n"
            f"  • Убедитесь, что группа есть на сайте колледжа\n"
            f"  • Попробуйте ввести номер заново"
        )
        btns = [
            [types.InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=back_callback)],
            [ButtonFactory.back("menu:start")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def schedule_not_found(date: str, group: str = None) -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка: расписание не найдено"""
        group_text = f" для группы {group}" if group else ""
        text = (
            f"❌ <b>Расписание на {date} не опубликовано{group_text}</b>\n\n"
            f"💡 <b>Возможные причины:</b>\n"
            f"  • Расписание еще не загружено на сайт\n"
            f"  • Выбрана дата в будущем\n"
            f"  • Технические проблемы на сайте колледжа\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Попробуйте позже (обычно расписание появляется вечером)\n"
            f"  • Проверьте другую дату\n"
            f"  • Обратитесь к администратору, если проблема сохраняется"
        )
        btns = [
            [types.InlineKeyboardButton(text="📅 Выбрать другую дату", callback_data="menu:show_calendar")],
            [ButtonFactory.back("menu:start")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def database_error(operation: str = "операции") -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка базы данных"""
        text = (
            f"❌ <b>Ошибка при выполнении {operation}</b>\n\n"
            f"💡 <b>Что произошло:</b>\n"
            f"  • Временная проблема с базой данных\n"
            f"  • Возможно, слишком много запросов\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Подождите несколько секунд\n"
            f"  • Попробуйте повторить действие\n"
            f"  • Если ошибка повторяется, обратитесь к администратору"
        )
        btns = [
            [types.InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="menu:start")],
            [ButtonFactory.close()]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def network_error() -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка сети"""
        text = (
            f"❌ <b>Ошибка подключения</b>\n\n"
            f"💡 <b>Что произошло:</b>\n"
            f"  • Не удалось подключиться к серверу колледжа\n"
            f"  • Возможно, сайт временно недоступен\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Проверьте интернет-соединение\n"
            f"  • Подождите несколько минут\n"
            f"  • Попробуйте снова"
        )
        btns = [
            [types.InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="menu:rasp")],
            [ButtonFactory.back("menu:start")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def invalid_input(field_name: str, example: str = None) -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка: неверный формат ввода"""
        example_text = f"\n\n📋 <b>Пример:</b> {example}" if example else ""
        text = (
            f"❌ <b>Неверный формат {field_name}</b>\n\n"
            f"💡 <b>Что не так:</b>\n"
            f"  • Введены некорректные данные\n"
            f"  • Не соответствует ожидаемому формату{example_text}\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Проверьте правильность ввода\n"
            f"  • Следуйте указанному формату\n"
            f"  • Попробуйте еще раз"
        )
        btns = [
            [ButtonFactory.cancel("menu:start")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def permission_error() -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка: недостаточно прав"""
        text = (
            f"❌ <b>Недостаточно прав</b>\n\n"
            f"💡 <b>Что произошло:</b>\n"
            f"  • У бота нет необходимых прав в чате\n"
            f"  • Требуются права администратора\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Выдайте боту права администратора\n"
            f"  • Убедитесь, что бот может закреплять сообщения\n"
            f"  • Попробуйте снова после выдачи прав"
        )
        btns = [
            [types.InlineKeyboardButton(text="✅ Проверить права", callback_data="check_pin_rights")],
            [ButtonFactory.close()]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def not_registered() -> tuple[str, types.InlineKeyboardMarkup]:
        """Ошибка: пользователь не зарегистрирован"""
        text = (
            f"❌ <b>Вы не зарегистрированы</b>\n\n"
            f"💡 <b>Что произошло:</b>\n"
            f"  • Вы еще не указали свою группу\n"
            f"  • Требуется регистрация для использования бота\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Нажмите кнопку ниже для регистрации\n"
            f"  • Укажите номер вашей группы\n"
            f"  • После регистрации все функции будут доступны"
        )
        btns = [
            [types.InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="menu:start")]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
    
    @staticmethod
    def generic_error(error_msg: str = None) -> tuple[str, types.InlineKeyboardMarkup]:
        """Общая ошибка"""
        error_details = f"\n\n🔍 <b>Детали:</b> <code>{error_msg}</code>" if error_msg else ""
        text = (
            f"❌ <b>Произошла ошибка</b>\n\n"
            f"💡 <b>Что произошло:</b>\n"
            f"  • Непредвиденная ошибка в работе бота{error_details}\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"  • Попробуйте повторить действие\n"
            f"  • Вернитесь в главное меню\n"
            f"  • Если ошибка повторяется, обратитесь к администратору"
        )
        btns = [
            [ButtonFactory.back("menu:start")],
            [ButtonFactory.close()]
        ]
        return text, types.InlineKeyboardMarkup(inline_keyboard=btns)
