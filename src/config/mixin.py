import os
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar, cast

import src.app.context as ctx
logger = ctx.services.logger
from src.app.paths import PATH_CONFIGS_USER
from src.config.constants import (
    CONFIG_INDENT,
    CONFIG_MISSING_DEFAULT,
    CONFIG_SAVE_RETRY_COUNT,
    CONFIG_SAVE_RETRY_DELAY_SEC,
)
from src.config.types import ConfigMap, ConfigMixinHost, ConfigValue
from src.config.utils import convert_value
from src.utils.filesystem import FS, del_safe, get_safe, set_safe

TDefault = TypeVar("TDefault")


class GetConfigMixin:
    def get(self: ConfigMixinHost, key: str, *, sep: str = ">", default: TDefault | object = CONFIG_MISSING_DEFAULT) -> object | TDefault | None:
        value = get_safe(self.data, key, sep=sep, default=CONFIG_MISSING_DEFAULT)
        if value is not CONFIG_MISSING_DEFAULT:
            return value
        if default is not CONFIG_MISSING_DEFAULT:
            return default

        default_value = get_safe(self.defaults, key, sep=sep, default=CONFIG_MISSING_DEFAULT)
        if default_value is not CONFIG_MISSING_DEFAULT:
            resolved_default = convert_value(None, cast(ConfigValue, default_value))
            return resolved_default

        return None


class SetConfigMixin:
    def set(self: ConfigMixinHost, key: str, value: object, *, sep: str = ">") -> None:
        default_value = get_safe(self.defaults, key, sep=sep, default=CONFIG_MISSING_DEFAULT)
        typed_default = cast(ConfigValue, default_value)
        value = convert_value(value, typed_default)

        normalized_default = convert_value(None, typed_default)
        if value == normalized_default:
            del_safe(self.data, key, sep=sep)
            logger.debug(f"resetted default to '{key.replace(sep, " > ")}'")
            return

        set_safe(self.data, key, cast(ConfigValue, value), sep=sep)
        logger.debug(f"setted '{value}' to '{key.replace(sep, " > ")}'")


class SaveConfigMixin:
    def _iter_ordered_items(self, data: ConfigMap, defaults: ConfigMap | None = None) -> Iterator[tuple[str, ConfigValue]]:
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

    def dump_dict(self, old_data: ConfigMap, defaults: ConfigMap | None = None, indent: int = 0) -> list[str]:
        new_data: list[str] = []
        indent_prefix = CONFIG_INDENT * indent
        for key, value in self._iter_ordered_items(old_data, defaults):
            child_defaults = defaults.get(key) if defaults is not None else None
            if isinstance(value, dict):
                new_data.append(f"{indent_prefix}{key}")
                new_data.extend(
                    self.dump_dict(
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

    def save(self: ConfigMixinHost) -> None:
        FS.ensure_dir(PATH_CONFIGS_USER)
        text = "\n".join(self.dump_dict(self.data, self.defaults))

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
                        logger.warning(f"can't replace file: {temp_file_path} to {self.path}, try: #{tries}")
                        if attempt == CONFIG_SAVE_RETRY_COUNT - 1:
                            raise
                        time.sleep(CONFIG_SAVE_RETRY_DELAY_SEC * tries)
            finally:
                if temp_file_path is not None:
                    try:
                        FS.delete_file(temp_file_path)
                    except OSError:
                        pass
