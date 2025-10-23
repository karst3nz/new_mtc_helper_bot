#!/bin/bash

# Скрипт для запуска MTC Helper Bot в Docker
# Использование: ./run.sh [команда]
# Команды: start, stop, restart, build, logs, shell

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Переходим в директорию со скриптом
cd "$(dirname "$0")"

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose не найден. Установите Docker Compose."
    exit 1
fi

# Функция для запуска
start_container() {
    print_message "Запуск MTC Helper Bot..."
    docker-compose up -d
    if [ $? -eq 0 ]; then
        print_message "✅ Контейнер успешно запущен"
        print_message "Для просмотра логов используйте: ./run.sh logs"
    else
        print_error "❌ Ошибка при запуске контейнера"
        exit 1
    fi
}

# Функция для остановки
stop_container() {
    print_message "Остановка MTC Helper Bot..."
    docker-compose down
    if [ $? -eq 0 ]; then
        print_message "✅ Контейнер успешно остановлен"
    else
        print_error "❌ Ошибка при остановке контейнера"
        exit 1
    fi
}

# Функция для перезапуска
restart_container() {
    print_message "Перезапуск MTC Helper Bot..."
    docker-compose restart
    if [ $? -eq 0 ]; then
        print_message "✅ Контейнер успешно перезапущен"
    else
        print_error "❌ Ошибка при перезапуске контейнера"
        exit 1
    fi
}

# Функция для сборки
build_container() {
    print_message "Сборка Docker образа..."
    docker-compose build --no-cache
    if [ $? -eq 0 ]; then
        print_message "✅ Образ успешно собран"
    else
        print_error "❌ Ошибка при сборке образа"
        exit 1
    fi
}

# Функция для просмотра логов
show_logs() {
    print_message "Показ логов MTC Helper Bot..."
    docker-compose logs -f
}

# Функция для входа в контейнер
shell_container() {
    print_message "Подключение к контейнеру..."
    docker-compose exec mtc-helper-bot /bin/bash
}

# Функция для показа статуса
show_status() {
    print_message "Статус контейнеров:"
    docker-compose ps
}

# Функция для показа помощи
show_help() {
    echo -e "${BLUE}MTC Helper Bot - Docker Management Script${NC}"
    echo ""
    echo "Использование: $0 [команда]"
    echo ""
    echo "Доступные команды:"
    echo "  start     - Запустить контейнер"
    echo "  stop      - Остановить контейнер"
    echo "  restart   - Перезапустить контейнер"
    echo "  build     - Собрать Docker образ"
    echo "  logs      - Показать логи контейнера"
    echo "  shell     - Подключиться к контейнеру"
    echo "  status    - Показать статус контейнеров"
    echo "  help      - Показать эту справку"
    echo ""
}

# Основная логика
case "${1:-help}" in
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    build)
        build_container
        ;;
    logs)
        show_logs
        ;;
    shell)
        shell_container
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
