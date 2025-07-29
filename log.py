import logging
from colorama import Fore, Style, init

init(autoreset=True)

LEVEL_COLORS = {
    logging.DEBUG:    Fore.CYAN,
    logging.INFO:     Fore.GREEN,
    logging.WARNING:  Fore.YELLOW,
    logging.ERROR:    Fore.RED,
    logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
}

class ColorFormatter(logging.Formatter):
    LEVEL_WIDTH = 8      # ширина столбца level
    NAME_WIDTH  = 18     # ширина столбца name

    def format(self, record):
        # cохраняем оригиналы, чтобы потом восстановить
        original_levelname = record.levelname
        original_name = record.name

        # — 1. подгоняем ширину столбцов —
        padded_level = original_levelname.center(self.LEVEL_WIDTH)
        record.name = original_name.center(self.NAME_WIDTH)

        # — 2. красим ТОЛЬКО levelname —
        color = LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{color}{padded_level}{Style.RESET_ALL}"

        try:
            return super().format(record)   # обычное форматирование
        finally:
            # вернём значения — важно, если есть другие хендлеры/форматтеры
            record.levelname = original_levelname
            record.name = original_name


def create_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    fmt = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # --- универсальные хендлеры (используем однажды) ---
    console = logging.StreamHandler()
    console.setFormatter(ColorFormatter(fmt, datefmt=datefmt))

    file_ = logging.FileHandler("app.log", encoding="utf-8")
    file_.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    # --- гарантируем, что root умеет выводить ---
    root = logging.getLogger()
    if not root.handlers:           # important: иначе дубли
        root.setLevel(level)
        root.addHandler(console)
        root.addHandler(file_)

    # --- конфигурируем наш собственный логгер ---
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:         # чтобы при повторном импорте не было множения
        logger.addHandler(console)
        logger.addHandler(file_)

    logger.propagate = False        # не отдаём наверх — иначе дублируется
    return logger


# Пример использования
if __name__ == "__main__":
    log = create_logger("test", level=logging.DEBUG)
    log.debug("Отладка")
    log.info("Информация")
    log.warning("Предупреждение")
    log.error("Ошибка")
    log.critical("Критическая ошибка")