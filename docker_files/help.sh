
#!/bin/bash

# MTC Helper Bot - Справочная система
# Показывает все доступные команды и их описание

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Функции для форматирования
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    MTC Helper Bot - Help                     ║${NC}"
    echo -e "${BLUE}║                       Docker справка                         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_command() {
    printf "  ${GREEN}%-15s${NC} %s\n" "$1" "$2"
}

print_example() {
    echo -e "  ${YELLOW}Пример:${NC} $1"
}

print_note() {
    echo -e "  ${PURPLE}💡 Примечание:${NC} $1"
}

print_warning() {
    echo -e "  ${RED}⚠️  Внимание:${NC} $1"
}

# Основная функция
show_help() {
    print_header
    
    print_section "🚀 БЫСТРЫЙ СТАРТ"
    echo -e "${YELLOW}Для быстрого развертывания выполните:${NC}"
    echo ""
    print_command "cd docker_files" "Перейти в папку Docker"
    print_command "./deploy.sh" "Полное развертывание (сжатие + сборка + запуск)"
    echo ""
    print_note "Эта команда автоматически сожмет проект, соберет Docker образ и запустит контейнер"
    echo ""
    
    print_section "📦 УПРАВЛЕНИЕ АРХИВАМИ"
    print_command "./compress.sh" "Создать архив с текущей датой"
    print_command "./compress.sh имя" "Создать архив с определенным именем"
    echo ""
    print_example "./compress.sh v1.2.3"
    print_note "Архивы сохраняются в папке docker_files/"
    echo ""
    
    print_section "🐳 УПРАВЛЕНИЕ DOCKER КОНТЕЙНЕРОМ"
    print_command "./run.sh start" "Запустить контейнер"
    print_command "./run.sh stop" "Остановить контейнер"
    print_command "./run.sh restart" "Перезапустить контейнер"
    print_command "./run.sh build" "Собрать Docker образ"
    print_command "./run.sh logs" "Показать логи контейнера"
    print_command "./run.sh shell" "Подключиться к контейнеру"
    print_command "./run.sh status" "Показать статус контейнеров"
    print_command "./run.sh help" "Показать справку по run.sh"
    echo ""
    
    print_section "📋 ПОШАГОВОЕ РАЗВЕРТЫВАНИЕ"
    echo -e "${YELLOW}Если хотите выполнить каждый шаг отдельно:${NC}"
    echo ""
    echo -e "  ${GREEN}1.${NC} Сжать проект:"
    print_example "./compress.sh"
    echo ""
    echo -e "  ${GREEN}2.${NC} Собрать образ:"
    print_example "./run.sh build"
    echo ""
    echo -e "  ${GREEN}3.${NC} Запустить контейнер:"
    print_example "./run.sh start"
    echo ""
    echo -e "  ${GREEN}4.${NC} Проверить логи:"
    print_example "./run.sh logs"
    echo ""
    
    print_section "🔧 ОТЛАДКА И МОНИТОРИНГ"
    print_command "docker ps" "Показать все запущенные контейнеры"
    print_command "docker logs mtc-helper-bot" "Показать логи напрямую"
    print_command "docker exec -it mtc-helper-bot bash" "Подключиться к контейнеру"
    print_command "docker stats mtc-helper-bot" "Показать использование ресурсов"
    echo ""
    
    print_section "📁 СТРУКТУРА ФАЙЛОВ"
    echo -e "  ${GREEN}compress.sh${NC}     - Сжатие проекта в архив"
    echo -e "  ${GREEN}deploy.sh${NC}       - Полное развертывание"
    echo -e "  ${GREEN}run.sh${NC}          - Управление контейнером"
    echo -e "  ${GREEN}help.sh${NC}         - Эта справка"
    echo -e "  ${GREEN}Dockerfile${NC}      - Конфигурация Docker образа"
    echo -e "  ${GREEN}docker-compose.yml${NC} - Конфигурация Docker Compose"
    echo -e "  ${GREEN}README_DOCKER.md${NC} - Подробная документация"
    echo ""
    
    print_section "❓ ПОЛУЧЕНИЕ ДОПОЛНИТЕЛЬНОЙ ПОМОЩИ"
    print_command "cat README_DOCKER.md" "Показать полную документацию"
    print_command "./run.sh help" "Справка по управлению контейнером"
    print_command "docker --help" "Справка по Docker"
    print_command "docker-compose --help" "Справка по Docker Compose"
    echo ""
    
    print_warning "Убедитесь, что Docker и Docker Compose установлены и запущены"
    echo ""
    
    print_section "🎯 ЧАСТО ИСПОЛЬЗУЕМЫЕ КОМАНДЫ"
    echo -e "  ${YELLOW}Полное развертывание:${NC}"
    echo -e "    ${GREEN}cd docker_files && ./deploy.sh${NC}"
    echo ""
    echo -e "  ${YELLOW}Просмотр логов:${NC}"
    echo -e "    ${GREEN}./run.sh logs${NC}"
    echo ""
    echo -e "  ${YELLOW}Остановка и очистка:${NC}"
    echo -e "    ${GREEN}./run.sh stop && docker system prune -f${NC}"
    echo ""
}

# Запуск справки
show_help