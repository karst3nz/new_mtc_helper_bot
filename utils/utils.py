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