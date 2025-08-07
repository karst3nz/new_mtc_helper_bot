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


def html_to_ansi(text: str) -> str:
    return (
        text
        # Жирный
        .replace("<b>", Style.BRIGHT)
        .replace("</b>", Style.NORMAL)
        .replace("<strong>", Style.BRIGHT)
        .replace("</strong>", Style.NORMAL)
        # Курсив
        .replace("<i>", Style.DIM)
        .replace("</i>", Style.NORMAL)
        .replace("<em>", Style.DIM)
        .replace("</em>", Style.NORMAL)
        # Зачёркнутый
        .replace("<s>", "\033[9m")
        .replace("</s>", Style.NORMAL)
        .replace("<strike>", "\033[9m")
        .replace("</strike>", Style.NORMAL)
        .replace("<del>", "\033[9m")
        .replace("</del>", Style.NORMAL)
        # Подчёркнутый
        .replace("<u>", "\033[4m")
        .replace("</u>", Style.NORMAL)
        # Код (однострочный)
        .replace("<code>", Fore.CYAN + Style.DIM)
        .replace("</code>", Style.RESET_ALL)
        # Преформатированный блок — можно стилизовать фоном
        .replace("<pre>", "\033[100m" + Fore.WHITE)
        .replace("</pre>", Style.RESET_ALL)
    )


class ColorFormatter(logging.Formatter):
    LEVEL_WIDTH = 8      # ширина столбца level
    NAME_WIDTH = 18      # ширина столбца name

    def format(self, record):
        original_levelname = record.levelname
        original_name = record.name
        padded_level = original_levelname.center(self.LEVEL_WIDTH)
        record.name = original_name.center(self.NAME_WIDTH)

        color = LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{color}{padded_level}{Style.RESET_ALL}"

        # преобразуем сообщение, если это строка
        if isinstance(record.msg, str):
            record.msg = html_to_ansi(record.msg)

        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname
            record.name = original_name


def create_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    fmt = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    console = logging.StreamHandler()
    console.setFormatter(ColorFormatter(fmt, datefmt=datefmt))

    file_ = logging.FileHandler("app.log", encoding="windows-1251")
    file_.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(level)
        root.addHandler(console)
        root.addHandler(file_)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        logger.addHandler(console)
        logger.addHandler(file_)

    logger.propagate = False
    return logger

# Пример использования
if __name__ == "__main__":
    log = create_logger("test", level=logging.DEBUG)
    log.debug("Отладка")
    log.info("Информация")
    log.warning("Предупреждение")
    log.error("Ошибка")
    log.critical("Критическая ошибка")