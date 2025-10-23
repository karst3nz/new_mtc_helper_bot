#!/bin/bash

# Полный скрипт развертывания MTC Helper Bot
# Автоматически сжимает проект, собирает и запускает Docker контейнер

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  MTC Helper Bot - Deploy Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

# Переходим в директорию со скриптом
cd "$(dirname "$0")"

print_header

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker не найден. Установите Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose не найден. Установите Docker Compose."
    exit 1
fi

# Шаг 1: Сжатие проекта
print_message "Шаг 1/4: Сжатие проекта..."
./compress.sh
if [ $? -ne 0 ]; then
    print_error "Ошибка при сжатии проекта"
    exit 1
fi

# Шаг 2: Остановка существующих контейнеров
print_message "Шаг 2/4: Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true

# Шаг 3: Сборка образа
print_message "Шаг 3/4: Сборка Docker образа..."
docker-compose build --no-cache
if [ $? -ne 0 ]; then
    print_error "Ошибка при сборке образа"
    exit 1
fi

# Шаг 4: Запуск контейнера
print_message "Шаг 4/4: Запуск контейнера..."
docker-compose up -d
if [ $? -ne 0 ]; then
    print_error "Ошибка при запуске контейнера"
    exit 1
fi

# Проверяем статус
sleep 3
print_message "Проверка статуса контейнера..."
docker-compose ps

echo ""
print_message "✅ Развертывание завершено успешно!"
echo ""
print_message "Полезные команды:"
echo "  Просмотр логов:    ./run.sh logs"
echo "  Остановка:         ./run.sh stop"
echo "  Перезапуск:        ./run.sh restart"
echo "  Статус:            ./run.sh status"
echo "  Подключение:       ./run.sh shell"
echo ""
