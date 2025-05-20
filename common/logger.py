import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Union

# ---------------------------------------------
# Настройки
# ---------------------------------------------

# Вычисляем корень проекта (поднимаемся на уровень выше текущего файла)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Цвета ANSI-escape для разных уровней логов
LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",       # серый
    logging.INFO: "\033[97m",        # белый
    logging.WARNING: "\033[93m",     # жёлтый
    logging.ERROR: "\033[91m",       # красный
    logging.CRITICAL: "\033[1;91m"   # ярко-красный
}
RESET = "\033[0m"  # сброс цвета


# ---------------------------------------------
# Форматтер с цветами и выравниванием
# ---------------------------------------------

class ColorFormatter(logging.Formatter):
    """
    Кастомный форматтер логов с цветами и выравниванием.
    Показывает: уровень | время | путь:строка | сообщение
    """

    def format(self, record: logging.LogRecord) -> str:
        # Укорачиваем путь, заменяя абсолютный корень проекта на ".."
        record.pathname = record.pathname.replace(PROJECT_ROOT, "..")

        color = LEVEL_COLORS.get(record.levelno, "")
        level = f"{record.levelname}".ljust(10)  # фиксированная ширина для выравнивания
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        path = f"{record.pathname}:{record.lineno:<4}"

        return f"{color}{level} | {time_str} | {path} | {record.getMessage()}{RESET}"


# ---------------------------------------------
# Кастомный логгер
# ---------------------------------------------

class CustomLogger(logging.Logger):
    """
    Логгер, который расширяет методы .error() и .critical()
    для отправки уведомлений (в будущем — Telegram, GitHub и т.п.)
    """

    def error(self, msg: str, *args, **kwargs) -> None:
        super().error(msg, *args, **kwargs)
        self._send_report('ERROR', msg, kwargs.get('exc_info'))

    def critical(self, msg: str, *args, **kwargs) -> None:
        super().critical(msg, *args, **kwargs)
        self._send_report('CRITICAL', msg, kwargs.get('exc_info'))

    def _send_report(self, level: str, msg: str, exc_info: Optional[Union[bool, BaseException, tuple]] = None) -> None:
        """
        Заглушка под отправку логов уровня ERROR и CRITICAL
        в Telegram, GitHub и т.д.
        """
        text = f"[{level}] {msg}"

        # Обработка исключения, если есть
        if exc_info:
            if isinstance(exc_info, BaseException):
                tb = "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            elif isinstance(exc_info, tuple):
                tb = "".join(traceback.format_exception(*exc_info))
            elif exc_info is True:
                tb = traceback.format_exc()
            else:
                tb = "⚠️ exc_info нераспознанного формата"

            text += f"\n{tb}"

        # Заглушка: просто печать в консоль
        print(f"[POST_PROCESS] {text}")


# ---------------------------------------------
# Инициализация логгера
# ---------------------------------------------

def get_logger(name: str = "app") -> CustomLogger:
    """
    Возвращает готовый кастомный логгер с цветами и хуками.
    Можно безопасно вызывать в любом модуле

    :param name: имя логгера
    :return: экземпляр CustomLogg.er
    """
    logging.setLoggerClass(CustomLogger)
    logger = logging.getLogger(name)

    # Добавляем хендлер только один раз
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
