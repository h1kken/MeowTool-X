from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_DEFAULT_CONFIG_LOADER
from src.config.defaults import default_config_loader
from src.config.mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS, get_safe
from src.config.enums import ConfigLoaderKey as CLKey

if TYPE_CHECKING:
    from pathlib import Path
    from src.config.types import ConfigMap
    

class ConfigLoader(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._path = PATH_DEFAULT_CONFIG_LOADER
        self._data: ConfigMap = {}
        self._defaults: ConfigMap = default_config_loader()
        self._save_lock = threading.Lock()
        self._load()

    @property
    def path(self) -> Path: return self._path

    @property
    def data(self) -> ConfigMap: return self._data

    @property
    def defaults(self) -> ConfigMap: return self._defaults

    @property
    def save_lock(self) -> threading.Lock: return self._save_lock

    def set(self, key: str, value: object, *, sep: str = ">") -> None:
        super().set(key, value, sep=sep)

        normalized_key = key.replace(sep, ">")
        if normalized_key.startswith(CLKey.MISC_DEBUGGER_PATH):
            self._apply_logger_settings()
        
        self.value_changed.emit(normalized_key, value)
        self.save()

    def _apply_logger_settings(self) -> None:
        logger.apply_debug_settings(
            debug=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_DEBUG, sep=">")
            ),
            info=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_INFO, sep=">")
            ),
            warning=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_WARNING, sep=">")
            ),
            error=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_ERROR, sep=">")
            ),
            exception=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_EXCEPTION, sep=">")
            ),
        )

    def _load(self) -> None:
        FS.ensure_file(self._path)

        try:
            with self._path.open("r", encoding="utf-8", errors="ignore") as f:
                parsed = parse_config(f.read())

            self._data = normalize_config(parsed, self._defaults)
            self._apply_logger_settings()
            self.save()
            self.config_loaded.emit()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Loader error: {e}")
