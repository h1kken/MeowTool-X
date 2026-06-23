from copy import deepcopy
import threading
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, Signal

from src.config.enums import ConfigLoaderKey as CLKey
from src.config.defaults import default_config
from src.config.loader import config_loader
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.paths import PATH_CONFIGS
from src.config.types import ConfigMap, ConfigValue
from src.config.utils import normalize_config, parse_config
from src.utils.filesystem import FS
from src.utils.logging import logger


class Config(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self, filename: str = "default") -> None:
        super().__init__()
        self.name = filename
        self._path: Path = PATH_CONFIGS / f"{filename}.txt"
        self._data: ConfigMap = {}
        self._defaults: ConfigMap = default_config()
        self._save_lock = threading.Lock()
        self.load(filename)


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

    def create_config(self, filename: str) -> None:
        path = PATH_CONFIGS / f"{filename}.txt"
        if path.exists():
            return

        FS.ensure_dir(PATH_CONFIGS)
        try:
            snapshot = deepcopy(self._data)
            text = "\n".join(self.dump_dict(snapshot, self._defaults))
            path.write_text(text, encoding="utf-8")
        except OSError as e:
            logger.exception(f"Can't create config '{filename}'. Error: {e}")
            return
        logger.info(f"Created config: {filename}")
        self.load(filename)

    def load(self, filename: str) -> None:
        logger.info(f"Initializing config: {filename}")
        self._path = PATH_CONFIGS / f"{filename}.txt"

        try:
            with self._path.open("r", encoding="utf-8", errors="ignore") as f:
                parsed_config = parse_config(f.read())

            self._data = normalize_config(parsed_config, self._defaults)
            self.save()
            self.name = self._path.stem

            logger.info(f"Config initialized: {filename}")
            self.config_loaded.emit()
        except FileNotFoundError:
            logger.warning("Config not found. Creating...")
            self.create_config(filename)
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Config can't be initialized. Error: {e}")

    def set(
        self, key: str, value: object, *, sep: str = ">", force_save: bool = False
    ) -> None:
        super().set(key, value, sep=sep)
        self.value_changed.emit(key.replace(sep, ">"), value)

        if config_loader.auto_save_config or force_save:
            self.save()

    def set_many(
        self,
        items: Mapping[str, ConfigValue] | Iterable[tuple[str, ConfigValue]],
        *,
        sep: str = ">",
        force_save: bool = False,
        emit_loaded: bool = False,
    ) -> None:
        iterable: list[tuple[str, ConfigValue]]
        if isinstance(items, Mapping):
            iterable = list(cast(Mapping[str, ConfigValue], items).items())
        else:
            iterable = list(items)
        for key, value in iterable:
            super().set(str(key), value, sep=sep)
            self.value_changed.emit(str(key).replace(sep, ">"), value)

        if config_loader.auto_save_config or force_save:
            self.save()

        if emit_loaded:
            self.config_loaded.emit()

    def reset(self, filename: str) -> None:
        path = PATH_CONFIGS / f"{filename}.txt"
        if not path.exists():
            return

        FS.ensure_dir(PATH_CONFIGS)
        FS.ensure_file(path, overwrite=True)

        if self.name == filename:
            self.load(filename)

    def delete(self, filename: str) -> None:
        FS.delete_file(PATH_CONFIGS / f"{filename}.txt")

    def rename(self, old_filename: str, new_filename: str) -> bool:
        old_name = str(old_filename).strip()
        new_name = str(new_filename).strip()

        if not all((old_name, new_name)):
            return False
        if old_name == new_name:
            return True

        old_path = PATH_CONFIGS / f"{old_name}.txt"
        new_path = PATH_CONFIGS / f"{new_name}.txt"
        if all((not old_path.exists(), new_path.exists())):
            return False

        try:
            old_path.rename(new_path)
        except OSError as e:
            logger.exception(
                f"Can't rename config '{old_name}' -> '{new_name}'. Error: {e}"
            )
            return False

        if self.name == old_name:
            self.name = new_name
            self._path = new_path
            self.config_loaded.emit()

        logger.debug(f"Renamed config: {old_name} -> {new_name}")
        return True

config = Config(str(config_loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default="default")))
