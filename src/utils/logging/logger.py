import sys
import loguru
from pathlib import Path
from datetime import datetime
from src.utils.consts import (
    PROGRAM_NAME, ASCII_MEOWTOOL,
    IS_LAUNCHED_WITH_CONSOLE,
    DATE_LOGGER_FORMAT,
    LOGGER_INDENT_NAME, LOGGER_INDENT_LINE,
    LOGGER_INDENT_FUNCTION, LOGGER_INDENT_LEVEL,
)
from src.utils.ansi import (
    RED, YELLOW, PINK,
    LIGHTGREEN, LIGHTYELLOW, LIGHTCYAN,
    CLEAR
)
from src.utils.logging.enums import LogLevel


def patcher(record: dict):
    name = record.get('name')
    if isinstance(name, str) and name.startswith('src.'):
        record['name'] = name.removeprefix('src.')


class Logger:
    def __init__(
        self,
        name: str = PROGRAM_NAME,
        *,
        stream: bool = IS_LAUNCHED_WITH_CONSOLE,
        console_level: LogLevel = LogLevel.DEBUG,
        file_level: LogLevel = LogLevel.DEBUG
    ):
        self._logger = loguru.logger
        self._logger.remove()
        self._logger.configure(patcher=patcher)
        
        self._path = Path(
            'Logs',
            f'{name} ({datetime.now().strftime(DATE_LOGGER_FORMAT)}).log'
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if stream:
            _logger_console_format = (
                '{lg}{{time:HH:mm:ss.SSS}} {yl}|{cl} '
                '{lc}{{name:>{name_i}}}:{{line:<{line_i}}} {yl}|{cl} '
                '{ly}{{function:<{function_i}}} {yl}|{cl} '
                '<level>{{level:<{level_i}}}</level> {yl}|{cl} '
                '<level>{{message}}</level>{cl}'
            ).format(
                lg = LIGHTGREEN,
                yl = YELLOW,
                lc = LIGHTCYAN,
                ly = LIGHTYELLOW,
                cl = CLEAR,
                name_i = LOGGER_INDENT_NAME,
                line_i = LOGGER_INDENT_LINE,
                function_i = LOGGER_INDENT_FUNCTION,
                level_i = LOGGER_INDENT_LEVEL
            )
            
            self._logger.add(
                sink=sys.stdout,
                level=console_level,
                format=_logger_console_format,
                colorize=True
            )
            self._logger.debug(
                f'{RED}[!] PROGRAM IS LAUNCHED IN TESTING MODE [!]\n'
                f'{PINK}{ASCII_MEOWTOOL}{CLEAR}'
            )

        _logger_file_format = (
            '{{time:HH:mm:ss.SSS}} | '
            '{{name:>{name_i}}}:{{line:<{line_i}}} | '
            '{{function:>{function_i}}} | '
            '{{level:<{level_i}}} | '
            '{{message}}'
        ).format(
            name_i = LOGGER_INDENT_NAME,
            line_i = LOGGER_INDENT_LINE,
            function_i = LOGGER_INDENT_FUNCTION,
            level_i = LOGGER_INDENT_LEVEL
        )
        
        self._logger.add(
            self._path,
            level=file_level,
            format=_logger_file_format,
            rotation='10 MB',
            retention=3,
            encoding='utf-8',
            enqueue=True
        )

    def debug(self, message: str = '') -> None: self._logger.opt(depth=1).debug(message)
    def info(self, message: str = '') -> None: self._logger.opt(depth=1).info(message)
    def warning(self, message: str = '') -> None: self._logger.opt(depth=1).warning(message)
    def error(self, message: str = '') -> None: self._logger.opt(depth=1).error(message)
    def exception(self, message: str = '') -> None: self._logger.opt(depth=1, exception=True).error(message)


logger = Logger()
