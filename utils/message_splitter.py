"""
Утилиты для обработки длинных сообщений и предотвращения переполнения
"""
from typing import List
from utils.log import create_logger

logger = create_logger(__name__)

# Максимальная длина сообщения в Telegram
MAX_MESSAGE_LENGTH = 4096


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Разбивает длинное сообщение на части по границам строк
    
    Args:
        text: Текст для разбиения
        max_length: Максимальная длина одной части (по умолчанию 4096)
        
    Returns:
        Список частей сообщения
        
    Example:
        >>> text = "Very long text..." * 1000
        >>> parts = split_message(text)
        >>> len(parts)
        3
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    lines = text.split('\n')
    current_part = ""
    
    for line in lines:
        # Если одна строка длиннее max_length, разбиваем её
        if len(line) > max_length:
            # Сохраняем текущую часть если есть
            if current_part:
                parts.append(current_part)
                current_part = ""
            
            # Разбиваем длинную строку по словам
            words = line.split(' ')
            for word in words:
                if len(current_part) + len(word) + 1 <= max_length:
                    current_part += word + ' '
                else:
                    if current_part:
                        parts.append(current_part.rstrip())
                    current_part = word + ' '
            continue
        
        # Проверяем, поместится ли строка в текущую часть
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + '\n'
        else:
            # Сохраняем текущую часть и начинаем новую
            if current_part:
                parts.append(current_part.rstrip())
            current_part = line + '\n'
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part.rstrip())
    
    logger.info(f"Split message into {len(parts)} parts")
    return parts


def truncate_text(text: str, max_length: int = MAX_MESSAGE_LENGTH, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины с добавлением суффикса
    
    Args:
        text: Текст для обрезки
        max_length: Максимальная длина
        suffix: Суффикс для добавления в конец (по умолчанию "...")
        
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    # Учитываем длину суффикса
    truncate_at = max_length - len(suffix)
    
    # Пытаемся обрезать по последнему пробелу
    truncated = text[:truncate_at]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + suffix


def format_schedule_compact(schedule_data: dict) -> str:
    """
    Форматирует расписание в компактном виде для экономии места
    
    Args:
        schedule_data: Данные расписания
        
    Returns:
        Отформатированная строка
    """
    # Сокращения для длинных названий
    abbreviations = {
        "Физическая культура": "Физ-ра",
        "Иностранный язык": "Ин.яз",
        "Информационные технологии": "ИТ",
        "Математика": "Мат-ка",
        "Белорусский язык": "Бел.яз",
        "Русский язык": "Рус.яз",
        "История": "Ист.",
        "Обществоведение": "Общ-ние",
        "Программирование": "Прогр.",
        "Базы данных": "БД",
    }
    
    result = []
    
    for lesson_num, lesson_info in schedule_data.items():
        subject = lesson_info.get('subject', '')
        
        # Применяем сокращения
        for full_name, abbr in abbreviations.items():
            if full_name in subject:
                subject = subject.replace(full_name, abbr)
        
        classroom = lesson_info.get('classroom', '')
        teacher = lesson_info.get('teacher', '')
        
        # Компактный формат
        line = f"{lesson_num}. {subject}"
        if classroom:
            line += f" | {classroom}"
        if teacher:
            # Сокращаем ФИО до инициалов
            teacher_parts = teacher.split()
            if len(teacher_parts) >= 2:
                teacher_short = f"{teacher_parts[0]} {teacher_parts[1][0]}."
                if len(teacher_parts) > 2:
                    teacher_short += f"{teacher_parts[2][0]}."
                line += f" | {teacher_short}"
        
        result.append(line)
    
    return '\n'.join(result)


def estimate_message_length(text: str, include_html: bool = True) -> int:
    """
    Оценивает длину сообщения с учетом HTML тегов
    
    Args:
        text: Текст сообщения
        include_html: Учитывать ли HTML теги
        
    Returns:
        Примерная длина сообщения
    """
    if not include_html:
        return len(text)
    
    # HTML теги не учитываются в лимите Telegram
    # Но для безопасности добавляем небольшой запас
    import re
    text_without_tags = re.sub(r'<[^>]+>', '', text)
    
    return len(text_without_tags)


def add_pagination_info(text: str, current_page: int, total_pages: int) -> str:
    """
    Добавляет информацию о пагинации к тексту
    
    Args:
        text: Исходный текст
        current_page: Номер текущей страницы
        total_pages: Общее количество страниц
        
    Returns:
        Текст с информацией о пагинации
    """
    if total_pages <= 1:
        return text
    
    pagination = f"\n\n📄 Страница {current_page} из {total_pages}"
    return text + pagination


def smart_truncate_schedule(schedule_text: str, max_length: int = MAX_MESSAGE_LENGTH) -> tuple[str, bool]:
    """
    Умная обрезка расписания с сохранением структуры
    
    Args:
        schedule_text: Текст расписания
        max_length: Максимальная длина
        
    Returns:
        Кортеж (обрезанный текст, был ли обрезан)
    """
    if len(schedule_text) <= max_length:
        return schedule_text, False
    
    lines = schedule_text.split('\n')
    result_lines = []
    current_length = 0
    truncated = False
    
    # Сохраняем заголовок (первые 3 строки обычно)
    header_lines = min(3, len(lines))
    for i in range(header_lines):
        result_lines.append(lines[i])
        current_length += len(lines[i]) + 1
    
    # Добавляем строки расписания пока помещаются
    footer = "\n\n⚠️ <i>Расписание обрезано. Используйте кнопки навигации для просмотра полного расписания.</i>"
    footer_length = len(footer)
    
    for i in range(header_lines, len(lines)):
        line = lines[i]
        if current_length + len(line) + 1 + footer_length <= max_length:
            result_lines.append(line)
            current_length += len(line) + 1
        else:
            truncated = True
            break
    
    result = '\n'.join(result_lines)
    if truncated:
        result += footer
    
    return result, truncated
