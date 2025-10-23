#!/bin/bash

# Скрипт для сжатия проекта в tar.gz архив
# Использование: ./compress.sh [имя_архива]

# Определяем имя архива
if [ -z "$1" ]; then
    ARCHIVE_NAME="mtc_helper_bot_$(date +%Y%m%d_%H%M%S).tar.gz"
else
    ARCHIVE_NAME="$1.tar.gz"
fi

echo "Создание архива: $ARCHIVE_NAME"

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.."

# Создаем архив, исключая ненужные файлы
tar -czf "docker_files/$ARCHIVE_NAME" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs' \
    --exclude='app.log' \
    --exclude='database/db.db' \
    --exclude='docker_files/*.tar.gz' \
    --exclude='.gitignore' \
    --exclude='*.log' \
    .

if [ $? -eq 0 ]; then
    echo "✅ Архив успешно создан: docker_files/$ARCHIVE_NAME"
    echo "📦 Размер архива: $(du -h "docker_files/$ARCHIVE_NAME" | cut -f1)"
else
    echo "❌ Ошибка при создании архива"
    exit 1
fi
