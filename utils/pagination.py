"""
Утилиты для пагинации списков в Telegram
"""
from typing import List, Tuple, Any
from aiogram import types
from math import ceil


class Paginator:
    """Класс для создания пагинации"""
    
    def __init__(self, items: List[Any], page: int = 1, per_page: int = 10):
        """
        Инициализация пагинатора
        
        Args:
            items: Список элементов
            page: Текущая страница (начиная с 1)
            per_page: Количество элементов на странице
        """
        self.items = items
        self.page = max(1, page)
        self.per_page = per_page
        self.total_items = len(items)
        self.total_pages = ceil(self.total_items / self.per_page) if self.total_items > 0 else 1
        
        # Корректируем страницу если она больше максимальной
        if self.page > self.total_pages:
            self.page = self.total_pages
    
    def get_page_items(self) -> List[Any]:
        """
        Получить элементы текущей страницы
        
        Returns:
            Список элементов для текущей страницы
        """
        start_idx = (self.page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        return self.items[start_idx:end_idx]
    
    def has_prev(self) -> bool:
        """Есть ли предыдущая страница"""
        return self.page > 1
    
    def has_next(self) -> bool:
        """Есть ли следующая страница"""
        return self.page < self.total_pages
    
    def get_page_info(self) -> str:
        """
        Получить информацию о текущей странице
        
        Returns:
            Строка вида "Страница 2 из 5 (всего: 47)"
        """
        return f"Страница {self.page} из {self.total_pages} (всего: {self.total_items})"
    
    def create_pagination_keyboard(self, callback_prefix: str, 
                                   additional_buttons: List[List[types.InlineKeyboardButton]] = None) -> types.InlineKeyboardMarkup:
        """
        Создать клавиатуру с кнопками пагинации
        
        Args:
            callback_prefix: Префикс для callback_data (например, "users_page")
            additional_buttons: Дополнительные кнопки для добавления в конец
        
        Returns:
            InlineKeyboardMarkup с кнопками пагинации
        """
        buttons = []
        
        # Создаем кнопки навигации
        nav_buttons = []
        
        if self.has_prev():
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"{callback_prefix}:{self.page - 1}"
                )
            )
        
        # Кнопка с номером текущей страницы (неактивная)
        nav_buttons.append(
            types.InlineKeyboardButton(
                text=f"· {self.page}/{self.total_pages} ·",
                callback_data="pagination:ignore"
            )
        )
        
        if self.has_next():
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="Вперед ▶️",
                    callback_data=f"{callback_prefix}:{self.page + 1}"
                )
            )
        
        buttons.append(nav_buttons)
        
        # Добавляем дополнительные кнопки если есть
        if additional_buttons:
            buttons.extend(additional_buttons)
        
        return types.InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_numbered_pagination_keyboard(self, callback_prefix: str, 
                                           max_buttons: int = 5,
                                           additional_buttons: List[List[types.InlineKeyboardButton]] = None) -> types.InlineKeyboardMarkup:
        """
        Создать клавиатуру с пронумерованными кнопками страниц
        
        Args:
            callback_prefix: Префикс для callback_data
            max_buttons: Максимальное количество кнопок с номерами страниц
            additional_buttons: Дополнительные кнопки
        
        Returns:
            InlineKeyboardMarkup с пронумерованными кнопками
        """
        buttons = []
        
        # Вычисляем диапазон страниц для отображения
        half_range = max_buttons // 2
        start_page = max(1, self.page - half_range)
        end_page = min(self.total_pages, start_page + max_buttons - 1)
        
        # Корректируем начало если конец упирается в максимум
        if end_page - start_page < max_buttons - 1:
            start_page = max(1, end_page - max_buttons + 1)
        
        # Создаем кнопки с номерами страниц
        page_buttons = []
        
        # Кнопка "в начало" если текущая страница далеко от начала
        if start_page > 1:
            page_buttons.append(
                types.InlineKeyboardButton(
                    text="⏮️",
                    callback_data=f"{callback_prefix}:1"
                )
            )
        
        # Кнопки с номерами страниц
        for page_num in range(start_page, end_page + 1):
            if page_num == self.page:
                # Текущая страница (выделена)
                text = f"[{page_num}]"
                callback = "pagination:ignore"
            else:
                text = str(page_num)
                callback = f"{callback_prefix}:{page_num}"
            
            page_buttons.append(
                types.InlineKeyboardButton(
                    text=text,
                    callback_data=callback
                )
            )
        
        # Кнопка "в конец" если текущая страница далеко от конца
        if end_page < self.total_pages:
            page_buttons.append(
                types.InlineKeyboardButton(
                    text="⏭️",
                    callback_data=f"{callback_prefix}:{self.total_pages}"
                )
            )
        
        buttons.append(page_buttons)
        
        # Добавляем дополнительные кнопки
        if additional_buttons:
            buttons.extend(additional_buttons)
        
        return types.InlineKeyboardMarkup(inline_keyboard=buttons)


def paginate_text(text: str, max_length: int = 4000) -> List[str]:
    """
    Разбить длинный текст на части для отправки в Telegram
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина одной части
    
    Returns:
        Список частей текста
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по строкам
    lines = text.split('\n')
    
    for line in lines:
        # Если добавление строки превысит лимит
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                # Строка сама по себе длиннее лимита - разбиваем её
                while len(line) > max_length:
                    parts.append(line[:max_length])
                    line = line[max_length:]
                current_part = line + '\n'
        else:
            current_part += line + '\n'
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)
    
    return parts


def create_list_with_pagination(items: List[str], page: int, per_page: int, 
                                callback_prefix: str, header: str = "",
                                additional_buttons: List[List[types.InlineKeyboardButton]] = None) -> Tuple[str, types.InlineKeyboardMarkup]:
    """
    Создать текст списка с пагинацией и клавиатуру
    
    Args:
        items: Список строк для отображения
        page: Текущая страница
        per_page: Элементов на странице
        callback_prefix: Префикс для callback
        header: Заголовок списка
        additional_buttons: Дополнительные кнопки
    
    Returns:
        Кортеж (текст, клавиатура)
    """
    paginator = Paginator(items, page, per_page)
    page_items = paginator.get_page_items()
    
    # Формируем текст
    text = header
    if header:
        text += "\n\n"
    
    text += "\n".join(page_items)
    text += f"\n\n{paginator.get_page_info()}"
    
    # Создаем клавиатуру
    keyboard = paginator.create_pagination_keyboard(callback_prefix, additional_buttons)
    
    return text, keyboard


def parse_page_callback(callback_data: str) -> Tuple[str, int]:
    """
    Распарсить callback_data пагинации
    
    Args:
        callback_data: Строка вида "prefix:page"
    
    Returns:
        Кортеж (prefix, page)
    """
    parts = callback_data.split(':')
    if len(parts) == 2:
        prefix = parts[0]
        try:
            page = int(parts[1])
            return prefix, page
        except ValueError:
            return prefix, 1
    return "", 1
