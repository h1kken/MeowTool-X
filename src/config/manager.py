from copy import deepcopy
from typing import Any

from PySide6.QtCore import QObject, Signal

from src.config.enums import ConfigLoaderKey as CLK
from src.config.defaults import default_config
from src.config.loader import config_loader
from src.config.mixin import GetConfigMixin, SaveConfigMixin, SetConfigMixin
from src.config.utils import normalize_config, parse_config
from src.utils.constants import PATH_CONFIGS
from src.utils.filesystem import FS
from src.utils.logging import logger


class Config(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = Signal()
    value_changed = Signal(str, object)

    def __init__(self, filename: str = "default"):
        super().__init__()
        self.name = filename
        self._path = None
        self._data = {}
        self._defaults = default_config()
        self.load(filename)

    def create_config(self, filename: str):
        path = PATH_CONFIGS / f"{filename}.txt"
        if path.exists():
            return

        FS.create_folder(PATH_CONFIGS)
        try:
            snapshot = deepcopy(self._data)
            text = "\n".join(self._dump_dict(snapshot, self._defaults))
            path.write_text(text, encoding="utf-8")
        except OSError as e:
            logger.exception(f"Can't create config '{filename}'. Error: {e}")
            return
        logger.info(f"Created config: {filename}")
        self.load(filename)

    def load(self, filename: str):
        logger.info(f"Initializing config: {filename}")
        self._path = PATH_CONFIGS / f"{filename}.txt"

        try:
            with open(self._path, "r", encoding="utf-8", errors="ignore") as f:
                parsed_config = parse_config(f.read())

            self._data = normalize_config(parsed_config, self._defaults)
            self.save()
            self.name = self._path.stem

            logger.info(f"Config initialized: {filename}")
            self.config_loaded.emit()
        except FileNotFoundError:
            logger.warning(f"Config not found. Creating...")
            self.create_config(filename)
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.exception(f"Config can't be initialized. Error: {e}")

    def set(
        self, key: str, value: Any, *, sep: str = ">", force_save: bool = False
    ) -> None:
        super().set(key, value, sep=sep)
        self.value_changed.emit(key.replace(sep, ">"), value)

        if config_loader.auto_save_config or force_save:
            self.save()

    def set_many(
        self,
        items: dict[str, Any] | list[tuple[str, Any]],
        *,
        sep: str = ">",
        force_save: bool = False,
        emit_loaded: bool = False,
    ) -> None:
        iterable = list(items.items() if isinstance(items, dict) else items)
        for key, value in iterable:
            super().set(str(key), value, sep=sep)
            self.value_changed.emit(str(key).replace(sep, ">"), value)

        if config_loader.auto_save_config or force_save:
            self.save()

        if emit_loaded:
            self.config_loaded.emit()

    def reset(self, filename: str):
        path = PATH_CONFIGS / f"{filename}.txt"
        if not path.exists():
            return

        FS.create_folder(PATH_CONFIGS)
        FS.create_clean_file(path)

        if self.name == filename:
            self.load(filename)

    def delete(self, filename: str):
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


config = Config(config_loader.get(CLK.LOADER_CONFIG_ON_LOAD, default="default"))
