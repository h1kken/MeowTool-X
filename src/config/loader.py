from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_DEFAULT_CONFIG_LOADER
from src.config.defaults import default_config_loader
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.types import ConfigMap
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS, get_safe
from src.config.enums import ConfigLoaderKey as CLKey


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
        self.auto_save_config = self.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, default=False)
        self.auto_save_theme = self.get(CLKey.SAVER_AUTO_SAVE_THEME_CHANGES, default=False)

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
        if normalized_key == CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES:
            self.auto_save_config = bool(value)
        if normalized_key == CLKey.SAVER_AUTO_SAVE_THEME_CHANGES:
            self.auto_save_theme = bool(value)
        if normalized_key.startswith(CLKey.MISC_DEBUGGER_PATH):
            self._apply_logger_settings()
        
        self.value_changed.emit(normalized_key, value)
        self.save()

    def _apply_logger_settings(self) -> None:
        logger.apply_debug_settings(
            debug=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_DEBUG, sep=">", default=False)
            ),
            info=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_INFO, sep=">", default=False)
            ),
            warning=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_WARNING, sep=">", default=False)
            ),
            error=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_ERROR, sep=">", default=False)
            ),
            exception=bool(
                get_safe(self._data, CLKey.MISC_DEBUGGER_EXCEPTION, sep=">", default=False)
            ),
        )

    def _load(self) -> None:
        FS.ensure_file(self.path)

        try:
            with self._path.open("r", encoding="utf-8", errors="ignore") as f:
                parsed = parse_config(f.read())

            self._data = normalize_config(parsed, self._defaults)
            self._apply_logger_settings()
            self.save()
            self.config_loaded.emit()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Loader error: {e}")
