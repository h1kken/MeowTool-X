import inspect
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import loguru

from src.app.paths import PATH_ROOT
from src.utils.constants.app import ASCII_MEOWTOOL, IS_LAUNCHED_WITH_CONSOLE, PROGRAM_NAME
from src.utils.constants.log import (
    DATE_LOGGER_FORMAT,
    LOGGER_INDENT_FUNCTION,
    LOGGER_INDENT_LEVEL,
    LOGGER_INDENT_LINE,
    LOGGER_INDENT_NAME,
    LOG_ORIGIN_DEFAULT,
)
from src.utils.ansi import (
    RED, YELLOW, PINK,
    LIGHTGREEN, LIGHTYELLOW, LIGHTCYAN,
    CLEAR
)
from src.utils.logging.enums import LogLevel

_LOG_ORIGIN: ContextVar[str] = ContextVar('log_origin', default=LOG_ORIGIN_DEFAULT)


def _capture_origin(depth: int = 1) -> str:
    frame = inspect.currentframe()
    if frame is None:
        return LOG_ORIGIN_DEFAULT
    for _ in range(depth + 1):
        frame = frame.f_back
        if frame is None:
            return LOG_ORIGIN_DEFAULT

    try:
        file_path = Path(frame.f_code.co_filename)
        
        try:
            file_path = file_path.resolve()
        except OSError:
            pass
        
        try:
            display_path = file_path.relative_to(PATH_ROOT).as_posix()
        except ValueError:
            display_path = file_path.as_posix()
            
        display_path = (
            display_path
            .removeprefix('src/')
            .removesuffix('.py')
            .replace('/', '.')
        )
            
        return f'{display_path}:{frame.f_lineno}'
    finally:
        del frame


def patcher(record: Any) -> None:
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
                display_path = path.relative_to(PATH_ROOT).as_posix()
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
        self._debugger_settings: dict[str, bool] = {}
        
        self.path = Path(
            'Logs',
            f'{name} ({datetime.now().strftime(DATE_LOGGER_FORMAT)}).log'
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        self._configure_sinks()

        if self._stream:
            self._logger.debug(
                f'{RED}[!] PROGRAM IS LAUNCHED IN TESTING MODE [!]\n'
                f'{PINK}{ASCII_MEOWTOOL}{CLEAR}'
            )

    def _resolve_record_kind(self, record: Any) -> str:
        extra = cast(dict[str, Any], record.get('extra') or {})
        kind = str(extra.get('meow_kind') or record['level'].name).strip().lower()
        match kind:
            case 'trace':
                return 'debug'
            case 'critical':
                return 'error'
            case _:
                return kind

    def _make_sink_filter(self) -> Any:
        def _filter(record: Any) -> bool:
            return self._debugger_settings.get(self._resolve_record_kind(record), True)
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
            self.path,
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
        updated: dict[str, bool] = dict(self._debugger_settings)
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
        
        self._debugger_settings = updated
        self._configure_sinks()
        return True

    @contextmanager
    def origin_scope(
        self,
        origin: str | None = None,
        *,
        overwrite: bool = False,
        depth: int = 1,
    ) -> Any:
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
