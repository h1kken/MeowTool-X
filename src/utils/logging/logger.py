import sys
import functools
import time
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Awaitable, Callable

import loguru
from aiohttp import ClientResponse

from src.utils.constants import (
    ROOT,
    PROGRAM_NAME,
    ASCII_MEOWTOOL,
    IS_LAUNCHED_WITH_CONSOLE,
    DATE_LOGGER_FORMAT,
    LOGGER_INDENT_NAME,
    LOGGER_INDENT_LINE,
    LOGGER_INDENT_FUNCTION,
    LOGGER_INDENT_LEVEL,
    LOG_ORIGIN_DEFAULT,
)
from src.utils.ansi import (
    RED, YELLOW, PINK,
    LIGHTGREEN, LIGHTYELLOW, LIGHTCYAN,
    CLEAR
)
from src.utils.logging.enums import LogLevel
from src.utils.constants import ROOT

_LOG_ORIGIN: ContextVar[str] = ContextVar('log_origin', default=LOG_ORIGIN_DEFAULT)


def _capture_origin(depth: int = 1) -> str:
    try:
        frame = sys._getframe(depth + 1)
    except ValueError:
        return LOG_ORIGIN_DEFAULT

    try:
        file_path = Path(frame.f_code.co_filename)
        
        try:
            file_path = file_path.resolve()
        except OSError:
            pass
        
        try:
            display_path = file_path.relative_to(ROOT).as_posix()
        except ValueError:
            display_path = file_path.as_posix()
            
        display_path = display_path.removesuffix('.py').replace('/', '.')
        
        if display_path.startswith('src.'):
            display_path = display_path.removeprefix('src.')
            
        return f'{display_path}:{frame.f_lineno}'
    finally:
        del frame


def patcher(record: dict):
    name = record.get('name')
    if isinstance(name, str) and name.startswith('src.'):
        record['name'] = name.removeprefix('src.')
    
    record.setdefault('extra', {})
    origin_path = _LOG_ORIGIN.get()
    origin_line = '-'
    
    if origin_path and origin_path != LOG_ORIGIN_DEFAULT and ':' in origin_path:
        origin_path, origin_line = origin_path.rsplit(':', 1)
    elif origin_path == LOG_ORIGIN_DEFAULT:
        file = record.get('file')
        file_path = getattr(file, 'path', None)
        line = record.get('line')
        
        if file_path and line:
            path = Path(file_path)
            
            try:
                path = path.resolve()
            except OSError:
                pass
            
            try:
                display_path = path.relative_to(ROOT).as_posix()
            except ValueError:
                display_path = path.as_posix()
                
            display_path = display_path.removesuffix('.py').replace('/', '.')
            
            if display_path.startswith('src.'):
                display_path = display_path.removeprefix('src.')
                
            origin_path = display_path
            origin_line = str(line)
        else:
            origin_path = LOG_ORIGIN_DEFAULT
            
    record['extra']['name'] = origin_path
    record['extra']['line'] = origin_line


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
        self._stream = bool(stream)
        self._console_level = console_level
        self._file_level = file_level
        
        self._path = Path(
            'Logs',
            f'{name} ({datetime.now().strftime(DATE_LOGGER_FORMAT)}).log'
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        self._debugger_settings = {
            'debug': True,
            'info': True,
            'warning': True,
            'error': True,
            'exception': True,
        }
        
        self._configure_sinks()

        if self._stream:
            self._logger.debug(
                f'{RED}[!] PROGRAM IS LAUNCHED IN TESTING MODE [!]\n'
                f'{PINK}{ASCII_MEOWTOOL}{CLEAR}'
            )

    def _resolve_record_kind(self, record):
        extra = record.get('extra') or {}
        kind = str(extra.get('meow_kind') or record['level'].name).strip().lower()
        match kind:
            case 'trace':
                return 'debug'
            case 'critical':
                return 'error'
            case _:
                return kind

    def _make_sink_filter(self):
        settings = dict(self._debugger_settings)
        def _filter(record):
            return settings.get(self._resolve_record_kind(record), True)
        return _filter

    def _configure_sinks(self) -> None:
        self._logger.remove()
        self._logger.configure(patcher=patcher)

        if self._stream:
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
                level=self._console_level,
                format=_logger_console_format,
                colorize=True,
                filter=self._make_sink_filter(),
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
            level=self._file_level,
            format=_logger_file_format,
            rotation='10 MB',
            retention=3,
            encoding='utf-8',
            enqueue=True,
            filter=self._make_sink_filter(),
        )

    def apply_debugger_settings(
        self,
        *,
        debug: bool | None = None,
        info: bool | None = None,
        warning: bool | None = None,
        error: bool | None = None,
        exception: bool | None = None,
    ) -> bool:
        updated = dict(self._debugger_settings)
        overrides = {
            'debug': debug,
            'info': info,
            'warning': warning,
            'error': error,
            'exception': exception,
        }
        for key, value in overrides.items():
            if value is None:
                continue
            updated[key] = bool(value)
        
        if updated == self._debugger_settings:
            return False
        
        self._debugger_settings = updated
        self._configure_sinks()
        return True

    @contextmanager
    def origin_scope(self, origin: str | None = None, *, overwrite: bool = False, depth: int = 1):
        current = _LOG_ORIGIN.get()
        if not overwrite and current != LOG_ORIGIN_DEFAULT:
            yield current
            return
        resolved = (origin or '').strip() or _capture_origin(depth=depth + 1)
        token = _LOG_ORIGIN.set(resolved)
        try:
            yield resolved
        finally:
            _LOG_ORIGIN.reset(token)

    def debug(self, message: str = '') -> None: self._logger.opt(depth=1).debug(message)
    def info(self, message: str = '') -> None: self._logger.opt(depth=1).info(message)
    def warning(self, message: str = '') -> None: self._logger.opt(depth=1).warning(message)
    def error(self, message: str = '') -> None: self._logger.opt(depth=1).error(message)
    def exception(self, message: str = '') -> None: self._logger.opt(depth=1, exception=True).error(message)


logger = Logger()


def log_action(action: str, *, re_raise: bool = False):
    def log_action_decorator(func):
        @functools.wraps(func)
        def log_action_wrapper(path: Path, *args, **kwargs):
            with logger.origin_scope(overwrite=False, depth=2):
                try:
                    return func(path, *args, **kwargs)
                except FileExistsError:
                    logger.debug(f'Can\'t {action} \'{path}\' that already exists')
                    if re_raise:
                        raise
                except Exception as e:
                    logger.exception(f'Can\'t {action}: {path}. Error: {type(e).__name__}')
                    if re_raise:
                        raise
        return log_action_wrapper
    return log_action_decorator


def log_network_request(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with logger.origin_scope(overwrite=False, depth=2):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            elapsed_ms = int((end - start) * 1000)
            if isinstance(result, ClientResponse):
                logger.debug(f'[{func.__name__.upper()}:{result.status}] {result.url} for {elapsed_ms}ms')
            return result
    return wrapper
