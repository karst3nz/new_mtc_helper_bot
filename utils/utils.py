from dataclasses import dataclass
from typing import Dict, Mapping



def format_and_return_columns(text):
    # Преобразуем текст в список кортежей
    data = [line.split(' - ') for line in text.splitlines()]

    # Сортировка по второму числу (в обратном порядке)
    sorted_data = sorted(data, key=lambda x: int(x[1]), reverse=True)

    # Создаем словарь для группировки по первой цифре
    groups = {}

    # Группировка данных по первой цифре
    for item in sorted_data:
        first_digit = item[0][0]
        if first_digit not in groups:
            groups[first_digit] = []
        groups[first_digit].append(f'{item[0]} - {item[1]}')

    # Сортируем группы по количеству элементов в них (по убыванию)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Определение максимальной длины группы для равномерного вывода
    max_length = max(len(group[1]) for group in sorted_groups)

    # Создание списка строк для вывода
    formatted_lines = []
    
    # Формирование строк для вывода
    for i in range(max_length):
        line_parts = []
        for group in sorted_groups:
            if i < len(group[1]):
                line_parts.append(group[1][i].ljust(12))  # Выравнивание по левому краю с шириной 12
            else:
                line_parts.append(' ' * 12)  # Добавление пустого пространства, если строка отсутствует
        formatted_lines.append("".join(line_parts))
    
    # Соединение всех строк в одну и возврат результата
    return "\n".join(formatted_lines)





SlotTimes = Dict[str, str]
ShiftSchedule = Dict[str, SlotTimes]


@dataclass(frozen=True)
class ShiftAccessor:
    """Provides attribute and key access to shifts (smena1/smena2)."""
    shifts: Mapping[str, SlotTimes]

    def __getitem__(self, key: str) -> SlotTimes:
        return self.shifts[key]

    def __getattr__(self, name: str) -> SlotTimes:
        key = {
            "smena1": "1",
            "smena2": "2",
            "_1smena": "1",
            "_2smena": "2",
        }.get(name, name)
        if key in self.shifts:
            return self.shifts[key]
        raise AttributeError(name)


@dataclass(frozen=True)
class LessonsTime:
    weekday: ShiftAccessor
    weekend: ShiftAccessor


def get_lessons_timeDT() -> LessonsTime:
    _WEEKDAY_1SMENA = {
        "1": "8:20 ‒ 9:05",  # Половина 1-ой пары
        "1/2": "9:15 ‒ 10:00",  # Конец 1-ой пары
        "2": "10:10 ‒ 10:55",  # Половина 2-ой пары
        "2/2": "11:05 ‒ 11:50",  # Конец 2-ой пары
        "3": "12:20 ‒ 13:05",
        "3/2": "13:15 ‒ 14:00",
        "4": "14:10 ‒ 14:55",
        "4/2": "15:00 ‒ 15:45",
        "5": "15:55 ‒ 16:40",
        "5/2": "16:45 ‒ 17:30",
        "6": "17:40 ‒ 18:25",
        "6/2": "18:30 ‒ 19:15",
        "7": "19:25 ‒ 20:10",
        "7/2": "20:15 ‒ 21:00",
    }

    _WEEKDAY_2SMENA = {
        **_WEEKDAY_1SMENA,
        "3": "12:00 ‒ 12:45",
        "3/2": "13:15 ‒ 14:00",
    }

    _WEEKEND = {
        "1/2": "8:20 ‒ 9:05",  # Половина 1-ой пары
        "1": "9:10 ‒ 9:55",  # Конец 1-ой пары
        "2/2": "10:10 ‒ 10:55",  # Половина 2-ой пары
        "2": "11:00 ‒ 11:45",  # Конец 2-ой пары
        "3/2": "11:55 ‒ 12:40",
        "3": "12:45 ‒ 13:30",
        "4/2": "13:40 ‒ 14:25",
        "4": "14:30 ‒ 15:15",
        "5/2": "15:25 ‒ 16:10",
        "5": "16:15 ‒ 17:00",
        "6/2": "17:10 ‒ 17:55",
        "6": "18:00 ‒ 18:45",
        "7/2": "18:55 ‒ 19:40",
        "7": "19:45 ‒ 20:30",
    }

    return LessonsTime(
        weekday=ShiftAccessor(
            shifts={
                "1": _WEEKDAY_1SMENA,
                "2": _WEEKDAY_2SMENA,
            }
        ),
        weekend=ShiftAccessor(
            shifts={
                "1": _WEEKEND,
                "2": _WEEKEND,
            }
        ),
    )


def get_lesson_time(lesson_num: str, start: bool, weekday: bool, smena: str): # lesson start in [time] if start == True or lesson ended in [time] if start == False
    lessons_time_dt = get_lessons_timeDT()
    shifts = lessons_time_dt.weekday if weekday else lessons_time_dt.weekend
    times = shifts.smena1 if smena == "1" else shifts.smena2
    lesson_key = lesson_num if start else lesson_num + "/2"
    lesson = times.get(lesson_key)
    return lesson.split(" ‒ ")[0] if start else lesson.split(" ‒ ")[1]



    