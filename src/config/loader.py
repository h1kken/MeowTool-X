from typing import Any

from PySide6.QtCore import QObject, Signal

from src.config.defaults import default_config_loader
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.utils import normalize_config, parse_config
from src.utils.constants import PATH_CONFIGS
from src.utils.filesystem import FS, get_safe
from src.utils.logging import logger
from src.utils.constants import (
    CONFIG_LOADER_AUTO_SAVE_CONFIG_FALLBACK,
    CONFIG_LOADER_AUTO_SAVE_THEME_FALLBACK,
    CONFIG_LOADER_LOG_DEBUG_FALLBACK,
    CONFIG_LOADER_LOG_ERROR_FALLBACK,
    CONFIG_LOADER_LOG_EXCEPTION_FALLBACK,
    CONFIG_LOADER_LOG_INFO_FALLBACK,
    CONFIG_LOADER_LOG_WARNING_FALLBACK,
)
from src.config.enums import ConfigLoaderKey as CLK


class ConfigLoader(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._path = None
        self._data = {}
        self._defaults = default_config_loader()
        self.auto_save_config = False
        self.auto_save_theme = False
        self._load()

    def set(self, key: str, value: Any, *, sep: str = ">") -> None:
        super().set(key, value, sep=sep)

        normalized_key = key.replace(sep, ">")
        if normalized_key == CLK.SAVER_AUTO_SAVE_CONFIG_CHANGES:
            self.auto_save_config = bool(value)
        if normalized_key == CLK.SAVER_AUTO_SAVE_THEME_CHANGES:
            self.auto_save_theme = bool(value)
        if normalized_key.startswith(CLK.MISC_DEBUGGER_PATH):
            self._apply_logger_settings()
        self.value_changed.emit(normalized_key, value)
        self.save()

    def _create_loader(self) -> None:
        if self._path.exists():
            return

        FS.create_folder(PATH_CONFIGS)
        FS.create_file(self._path)
        logger.info("Loader created")
        self._load()

    def _apply_runtime_settings(self) -> None:
        self.auto_save_config = bool(
            get_safe(
                self._data,
                CLK.SAVER_AUTO_SAVE_CONFIG_CHANGES,
                sep=">",
                default=CONFIG_LOADER_AUTO_SAVE_CONFIG_FALLBACK,
            )
        )
        self.auto_save_theme = bool(
            get_safe(
                self._data,
                CLK.SAVER_AUTO_SAVE_THEME_CHANGES,
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
                    CLK.MISC_DEBUGGER_DEBUG,
                    sep=">",
                    default=CONFIG_LOADER_LOG_DEBUG_FALLBACK,
                )
            ),
            info=bool(
                get_safe(
                    self._data,
                    CLK.MISC_DEBUGGER_ERROR,
                    sep=">",
                    default=CONFIG_LOADER_LOG_INFO_FALLBACK,
                )
            ),
            warning=bool(
                get_safe(
                    self._data,
                    CLK.MISC_DEBUGGER_EXCEPTION,
                    sep=">",
                    default=CONFIG_LOADER_LOG_WARNING_FALLBACK,
                )
            ),
            error=bool(
                get_safe(
                    self._data,
                    CLK.MISC_DEBUGGER_INFO,
                    sep=">",
                    default=CONFIG_LOADER_LOG_ERROR_FALLBACK,
                )
            ),
            exception=bool(
                get_safe(
                    self._data,
                    CLK.MISC_DEBUGGER_WARNING,
                    sep=">",
                    default=CONFIG_LOADER_LOG_EXCEPTION_FALLBACK,
                )
            ),
        )

    def _load(self) -> None:
        logger.info("Initializing loader...")
        self._path = PATH_CONFIGS / ".Loader.txt"

        try:
            with open(self._path, "r", encoding="utf-8", errors="ignore") as f:
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
