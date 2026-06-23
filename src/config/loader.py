import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.config.constants import (
    CONFIG_LOADER_AUTO_SAVE_CONFIG_FALLBACK,
    CONFIG_LOADER_AUTO_SAVE_THEME_FALLBACK,
    CONFIG_LOADER_LOG_DEBUG_FALLBACK,
    CONFIG_LOADER_LOG_ERROR_FALLBACK,
    CONFIG_LOADER_LOG_EXCEPTION_FALLBACK,
    CONFIG_LOADER_LOG_INFO_FALLBACK,
    CONFIG_LOADER_LOG_WARNING_FALLBACK,
)
from src.config.defaults import default_config_loader
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.paths import PATH_CONFIGS
from src.config.types import ConfigMap
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS, get_safe
from src.config.enums import ConfigLoaderKey as CLKey
from src.utils.logging import logger


class ConfigLoader(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._path: Path = PATH_CONFIGS / ".Loader.txt"
        self._data: ConfigMap = {}
        self._defaults: ConfigMap = default_config_loader()
        self._save_lock = threading.Lock()
        self.auto_save_config = False
        self.auto_save_theme = False
        self._load()

    @property
    def data(self) -> ConfigMap:
        return self._data

    @property
    def defaults(self) -> ConfigMap:
        return self._defaults

    @property
    def path(self) -> Path:
        return self._path

    @property
    def save_lock(self) -> threading.Lock:
        return self._save_lock

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

    def _create_loader(self) -> None:
        if self._path.exists():
            return

        FS.ensure_dir(PATH_CONFIGS)
        FS.ensure_file(self._path)
        logger.info("Loader created")
        self._load()

    def _apply_runtime_settings(self) -> None:
        self.auto_save_config = bool(
            get_safe(
                self._data,
                CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES,
                sep=">",
                default=CONFIG_LOADER_AUTO_SAVE_CONFIG_FALLBACK,
            )
        )
        self.auto_save_theme = bool(
            get_safe(
                self._data,
                CLKey.SAVER_AUTO_SAVE_THEME_CHANGES,
                sep=">",
                default=CONFIG_LOADER_AUTO_SAVE_THEME_FALLBACK,
            )
        )
        self._apply_logger_settings()

    def _apply_logger_settings(self) -> None:
        logger.apply_debugger_settings(
            debug=bool(
                get_safe(
                    self._data,
                    CLKey.MISC_DEBUGGER_DEBUG,
                    sep=">",
                    default=CONFIG_LOADER_LOG_DEBUG_FALLBACK,
                )
            ),
            info=bool(
                get_safe(
                    self._data,
                    CLKey.MISC_DEBUGGER_ERROR,
                    sep=">",
                    default=CONFIG_LOADER_LOG_INFO_FALLBACK,
                )
            ),
            warning=bool(
                get_safe(
                    self._data,
                    CLKey.MISC_DEBUGGER_EXCEPTION,
                    sep=">",
                    default=CONFIG_LOADER_LOG_WARNING_FALLBACK,
                )
            ),
            error=bool(
                get_safe(
                    self._data,
                    CLKey.MISC_DEBUGGER_INFO,
                    sep=">",
                    default=CONFIG_LOADER_LOG_ERROR_FALLBACK,
                )
            ),
            exception=bool(
                get_safe(
                    self._data,
                    CLKey.MISC_DEBUGGER_WARNING,
                    sep=">",
                    default=CONFIG_LOADER_LOG_EXCEPTION_FALLBACK,
                )
            ),
        )

    def _load(self) -> None:
        logger.info("Initializing loader...")

        try:
            with self._path.open("r", encoding="utf-8", errors="ignore") as f:
                parsed_config_loader = parse_config(f.read())

            self._data = normalize_config(parsed_config_loader, self._defaults, keep_unknown=False)
            self._apply_runtime_settings()
            self.save()
            logger.info("Loader initialized")
            self.config_loaded.emit()
        except FileNotFoundError:
            logger.warning("Loader not found. Creating...")
            self._create_loader()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Loader can't be initialized. Error: {e}")


config_loader = ConfigLoader()
