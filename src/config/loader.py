from __future__ import annotations

import typing as t

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_DEFAULT_LOADER
from src.config.defaults import default_config_loader
from src.config.mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS
from src.config.enums import ConfigLoaderKey as CLKey

if t.TYPE_CHECKING:
    from src.core.types import DataMap
    

class ConfigLoader(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    configLoaded = Signal()
    valueChanged = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        
        self._path = PATH_DEFAULT_LOADER
        self._data: DataMap = {}
        self._defaults: DataMap = default_config_loader()
        self._save_lock = threading.Lock()
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def data(self) -> DataMap:
        return self._data

    @property
    def defaults(self) -> DataMap:
        return self._defaults

    @property
    def save_lock(self) -> threading.Lock:
        return self._save_lock

    def set(self, key: str, value: object, *, sep: str = '>') -> None:
        super().set(key, value, sep=sep)

        normalized_key = key.replace(sep, '>')
        if normalized_key.startswith(CLKey.MISC_DEBUGGER_PATH):
            self._apply_logger_settings()
        
        self.valueChanged.emit(normalized_key, value)
        self.save()

    def _apply_logger_settings(self) -> None:
        logger.apply_debug_settings(
            debug=bool(self.get(CLKey.MISC_DEBUGGER_DEBUG)),
            info=bool(self.get(CLKey.MISC_DEBUGGER_INFO)),
            warning=bool(self.get(CLKey.MISC_DEBUGGER_WARNING)),
            error=bool(self.get(CLKey.MISC_DEBUGGER_ERROR)),
            exception=bool(self.get(CLKey.MISC_DEBUGGER_EXCEPTION)),
        )

    def _load(self) -> None:
        FS.ensure_file(self._path)

        try:
            with self._path.open('r', encoding='utf-8', errors='ignore') as f:
                parsed = parse_config(f.read())

            self._data = normalize_config(parsed, self._defaults, recovery_missing=True)
            self._apply_logger_settings()
            self.save()
            self.configLoaded.emit()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f'Loader error: {e}')
