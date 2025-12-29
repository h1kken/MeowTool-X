import sys
import loguru
from datetime import datetime
from pathlib import Path
from src.utils.consts import IS_LAUNCHED_WITH_CONSOLE, PATH_LOGGER
from src.utils.ansi import (
    RED,
    YELLOW,
    LIGHTGREEN,
    LIGHTYELLOW,
    LIGHTCYAN,
    CLEAR
)


def patcher(record: dict):
    name = record.get('name')
    if isinstance(name, str) and name.startswith('src.'):
        record['name'] = name.removeprefix('src.')


class Logger:
    def __init__(
        self,
        *,
        stream: bool = IS_LAUNCHED_WITH_CONSOLE,
        level: str = 'DEBUG'
    ):
        self._logger = loguru.logger
        self._logger.remove()
        
        self._logger.configure(patcher=patcher)
        
        self._path = PATH_LOGGER
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if stream:
            _logger_console_format = (
                f'{LIGHTGREEN}'
                '{time:HH:mm:ss.SSS}'
                f' {YELLOW}| {LIGHTCYAN}'
                '{name:>25}'
                f'{CLEAR}:{LIGHTCYAN}'
                '{line:<4}'
                f' {YELLOW}| {LIGHTYELLOW}'
                '{function:<20}'
                f' {YELLOW}| {CLEAR}'
                '<level>{level:<7}</level>'
                f' {YELLOW}| {CLEAR}'
                '<level>{message}</level>'
            )
            
            self._logger.add(
                sink=sys.stdout,
                level=level,
                format=_logger_console_format,
                colorize=True
            )
            self._logger.debug(f'{RED}[!] PROGRAM IS LAUNCHED IN TESTING MODE [!]{CLEAR}')

        _logger_file_format = (
            '{time:HH:mm:ss.SSS} | '
            '{name:>25}:{line:<4} | '
            '{function:>20} | '
            '{level:<7} | '
            '{message}'
        )
        
        self._logger.add(
            self._path,
            level=level,
            format=_logger_file_format,
            rotation='5 MB',
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