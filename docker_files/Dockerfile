# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY req.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r req.txt

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p logs database

# Создаем базу данных SQLite если её нет
RUN touch database/db.db

# Устанавливаем права на базу данных
RUN chmod 666 database/db.db

# Открываем порт (если нужен)
# EXPOSE 8000

# Команда по умолчанию
CMD ["python", "main.py"]
