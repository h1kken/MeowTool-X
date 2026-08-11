from __future__ import annotations

import typing as t
import collections.abc as cabc

from copy import deepcopy
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_CONFIGS_USER, PATH_DEFAULT_CONFIG
from src.config.defaults import default_config
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.types import ConfigMap, ConfigValue
from src.config.utils import normalize_config, parse_config
from src.config.enums import ConfigLoaderKey as CLKey
from src.utils.filesystem import FS

if t.TYPE_CHECKING:
    from src.config import ConfigLoader


class Config(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    configLoaded = Signal()
    valueChanged = Signal(str, object)

    def __init__(self, loader: ConfigLoader) -> None:
        super().__init__()
        self.loader = loader
        
        self._path = PATH_DEFAULT_CONFIG
        self._data: ConfigMap = {}
        self._defaults: ConfigMap = default_config()
        self._save_lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def data(self) -> ConfigMap:
        return self._data

    @property
    def defaults(self) -> ConfigMap:
        return self._defaults

    @property
    def save_lock(self) -> threading.Lock:
        return self._save_lock
    
    def load(self, name: str | None = None) -> None:
        if name is None:
            name = str(self.loader.get(CLKey.LOADER_CONFIG_ON_LOAD)).strip()
        
        path = PATH_CONFIGS_USER / f'{name}.txt'
        if not path.is_file():
            return
        
        try:
            with path.open('r', encoding='utf-8') as f:
                parsed = parse_config(f.read())

            self._data = normalize_config(parsed, self._defaults)
            self._path = path
            self.save()
            self.configLoaded.emit()
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f'Can\'t load config \'{name}\': {e}')

    def create(self, name: str, *, overwrite: bool = False) -> None:
        path = PATH_CONFIGS_USER / f'{name}.txt'
        if path.is_file() and not overwrite:
            return

        FS.ensure_dir(PATH_CONFIGS_USER)
        try:
            snapshot = deepcopy(self._data)
            text = '\n'.join(self.dump_dict(snapshot, self._defaults))
            path.write_text(text, encoding='utf-8')
        except OSError as e:
            logger.exception(f'Can\'t create config \'{name}\': {e}')

    def set(self, key: str, value: object, *, sep: str = '>', force_save: bool = False) -> None:
        super().set(key, value, sep=sep)
        self.valueChanged.emit(key.replace(sep, '>'), value)

        if self.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES) or force_save:
            self.save()

    def set_many(self, items: cabc.Mapping[str, ConfigValue] | cabc.Iterable[tuple[str, ConfigValue]], *, sep: str = '>', force_save: bool = False) -> None:
        lst: list[tuple[str, ConfigValue]] = list(t.cast(cabc.Mapping[str, ConfigValue], items).items()) if isinstance(items, cabc.Mapping) else list(items)
        for key, value in lst:
            super().set(str(key), value, sep=sep)
            self.valueChanged.emit(str(key).replace(sep, '>'), value)

        if self.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES) or force_save:
            self.save()

    def rename(self, old_name: str, new_name: str) -> bool:
        old_path = PATH_CONFIGS_USER / f'{old_name}.txt'
        new_path = PATH_CONFIGS_USER / f'{new_name}.txt'
        if (
            old_path == new_path
            or old_path.is_file()
            or new_path.is_file()
        ):
            return False

        try:
            old_path.rename(new_path)
            self._path = new_path
            return True
        except OSError as e:
            logger.exception(f'Can\'t rename config \'{old_name}.txt\' to \'{new_name}.txt\': {e}')
            return False
