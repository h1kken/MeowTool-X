from __future__ import annotations

from copy import deepcopy
import threading
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_CONFIGS_USER, PATH_DEFAULT_CONFIG
from src.config.defaults import default_config
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.types import ConfigMap, ConfigValue
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS
from src.config import ConfigLoaderKey as CLKey

if TYPE_CHECKING:
    from src.config import ConfigLoader


class Config(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self, loader: ConfigLoader) -> None:
        super().__init__()
        self.loader = loader
        
        self._path = PATH_DEFAULT_CONFIG
        self._data: ConfigMap = {}
        self._defaults: ConfigMap = default_config()
        self._save_lock = threading.Lock()

    @property
    def path(self) -> Path: return self._path

    @property
    def data(self) -> ConfigMap: return self._data

    @property
    def defaults(self) -> ConfigMap: return self._defaults

    @property
    def save_lock(self) -> threading.Lock: return self._save_lock

    def create_config(self, filename: str) -> None:
        path = PATH_CONFIGS_USER / f"{filename}.txt"
        if path.exists():
            return

        FS.ensure_dir(PATH_CONFIGS_USER)
        try:
            snapshot = deepcopy(self._data)
            text = "\n".join(self.dump_dict(snapshot, self._defaults))
            path.write_text(text, encoding="utf-8")
            self.load(filename)
        except OSError as e:
            logger.exception(f"Can't create config '{filename}'. Error: {e}")
        
    def load(self, filename: str | None = None) -> None:
        if filename is None:
            filename = str(self.loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default=PATH_DEFAULT_CONFIG.stem)).strip()
        
        path = PATH_CONFIGS_USER / f"{filename}.txt"
        if not path.is_file():
            return
        
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                parsed = parse_config(f.read())

            self._data = normalize_config(parsed, self._defaults)
            self._path = path
            self.save()
            self.config_loaded.emit()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Can't load config '{filename}'. Error: {e}")

    def set(self, key: str, value: object, *, sep: str = ">", force_save: bool = False) -> None:
        super().set(key, value, sep=sep)
        self.value_changed.emit(key.replace(sep, ">"), value)

        if self.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, default=False) or force_save:
            self.save()

    def set_many(self, items: Mapping[str, ConfigValue] | Iterable[tuple[str, ConfigValue]], *, sep: str = ">", force_save: bool = False) -> None:
        lst: list[tuple[str, ConfigValue]] = list(cast(Mapping[str, ConfigValue], items).items()) if isinstance(items, Mapping) else list(items)
        for key, value in lst:
            super().set(str(key), value, sep=sep)
            self.value_changed.emit(str(key).replace(sep, ">"), value)

        if self.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, default=False) or force_save:
            self.save()

    def rename(self, path: Path, name: Path) -> None:
        if not path.is_file():
            return
        if path.stem == name:
            return

        new_path = PATH_CONFIGS_USER / f"{name}.txt"
        if new_path.is_file():
            return

        try:
            path.rename(new_path)
            self._path = new_path
        except OSError as e:
            logger.exception(f"Can't rename config '{path.stem}' to '{name}'. Error: {e}")
            return
