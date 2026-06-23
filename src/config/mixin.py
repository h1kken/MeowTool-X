import os
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar, cast

from src.config.constants import (
    CONFIG_INDENT,
    CONFIG_MISSING_DEFAULT,
    CONFIG_SAVE_RETRY_COUNT,
    CONFIG_SAVE_RETRY_DELAY_SEC,
)
from src.config.paths import PATH_CONFIGS
from src.config.types import ConfigMap, ConfigMixinHost, ConfigValue
from src.config.utils import convert_value
from src.utils.filesystem import FS, del_safe, get_safe, set_safe
from src.utils.logging import logger

_CONFIG_DEFAULT_SENTINEL = object()
TDefault = TypeVar("TDefault")


class GetConfigMixin:
    def get(
        self: ConfigMixinHost,
        key: str,
        *,
        sep: str = ">",
        default: TDefault | object = _CONFIG_DEFAULT_SENTINEL,
    ) -> object | TDefault | None:
        missing = _CONFIG_DEFAULT_SENTINEL
        value = get_safe(self.data, key, sep=sep, default=missing)

        if value is not missing:
            logger.debug(f"Loaded '{value}' from '{key.replace(sep, ' > ')}'")
            return value

        if default is not missing:
            logger.debug(f"Loaded fallback '{default}' from explicit default for '{key.replace(sep, ' > ')}'")
            return default

        default_value = get_safe(self.defaults, key, sep=sep, default=missing)
        if default_value is not missing:
            resolved_default = convert_value(None, cast(ConfigValue, default_value))
            logger.debug(f"Loaded fallback '{resolved_default}' from defaults for '{key.replace(sep, ' > ')}'")
            return resolved_default

        logger.debug(f"Loaded 'None' from '{key.replace(sep, ' > ')}'")
        return None


class SetConfigMixin:
    def set(self: ConfigMixinHost, key: str, value: object, *, sep: str = ">") -> None:
        default_value = get_safe(self.defaults, key, sep=sep, default=CONFIG_MISSING_DEFAULT)
        has_default = default_value is not CONFIG_MISSING_DEFAULT
        typed_default = cast(ConfigValue, default_value) if has_default else None
        value = convert_value(value, typed_default)

        if has_default:
            normalized_default = convert_value(None, typed_default)
            if value == normalized_default:
                del_safe(self.data, key, sep=sep)
                logger.debug(f"Reset to default '{key.replace(sep, ' > ')}'")
                return

        set_safe(self.data, key, cast(ConfigValue, value), sep=sep)
        logger.debug(f"Setted '{value}' to '{key.replace(sep, ' > ')}'")


class SaveConfigMixin:
    def _iter_ordered_items(
        self,
        data: ConfigMap,
        defaults: ConfigMap | None = None,
    ) -> Iterator[tuple[str, ConfigValue]]:
        if defaults is None:
            yield from data.items()
            return

        yielded: set[str] = set()

        for key in defaults:
            if key in data:
                yielded.add(key)
                yield key, data[key]

        for key, value in data.items():
            if key in yielded:
                continue
            yield key, value

    def _dump_dict(
        self,
        old_data: ConfigMap,
        defaults: ConfigMap | None = None,
        indent: int = 0,
    ) -> list[str]:
        new_data: list[str] = []
        indent_prefix = CONFIG_INDENT * indent
        for key, value in self._iter_ordered_items(old_data, defaults):
            child_defaults = defaults.get(key) if defaults is not None else None
            if isinstance(value, dict):
                new_data.append(f"{indent_prefix}{key}")
                new_data.extend(
                    self._dump_dict(
                        value,
                        child_defaults if isinstance(child_defaults, dict) else None,
                        indent + 1,
                    )
                )
            else:
                if type(value) is bool:
                    value = "Yes" if value else "No"
                new_data.append(f"{indent_prefix}{key}: {value}")
        return new_data

    def dump_dict(
        self,
        old_data: ConfigMap,
        defaults: ConfigMap | None = None,
        indent: int = 0,
    ) -> list[str]:
        return self._dump_dict(old_data, defaults, indent)

    def save(self: ConfigMixinHost) -> None:
        FS.ensure_dir(PATH_CONFIGS)
        lines = self.dump_dict(self.data, self.defaults)
        text = "\n".join(lines)

        with self.save_lock:
            temp_file_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    delete=False,
                    dir=self.path.parent,
                    prefix=f"{self.path.stem}.",
                    suffix=".tmp",
                ) as temp_file:
                    temp_file.write(text)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                    temp_file_path = Path(temp_file.name)

                for attempt in range(CONFIG_SAVE_RETRY_COUNT):
                    try:
                        FS.replace_file(temp_file_path, self.path)
                        break
                    except PermissionError:
                        tries = attempt + 1
                        logger.debug(f"Can't save replace file: {temp_file_path} to {self.path}. Try: {tries}")
                        if attempt == CONFIG_SAVE_RETRY_COUNT - 1:
                            raise
                        time.sleep(CONFIG_SAVE_RETRY_DELAY_SEC * tries)
            finally:
                if temp_file_path is not None:
                    try:
                        FS.delete_file(temp_file_path)
                    except OSError:
                        pass
        logger.debug(f"Config '{self.path.stem}' is saved")
