import typing as t
import collections.abc as cabc

import os
import tempfile
import time
from pathlib import Path

from src.utils.logging import logger
from src.app.paths import PATH_CONFIGS
from src.config.constants import CONFIG_INDENT, CONFIG_MISSING_DEFAULT, CONFIG_SAVE_RETRY_COUNT, CONFIG_SAVE_RETRY_DELAY_SEC
from src.config.types import ConfigMap, ConfigMixinHost, ConfigValue
from src.config.utils import convert_value
from src.utils.filesystem import FS, del_safe, get_safe, set_safe


class GetConfigMixin:
    def get(self: ConfigMixinHost, key: str, *, sep: str = '>') -> ConfigValue:
        value = t.cast(ConfigValue, get_safe(self.data, key, sep=sep, default=CONFIG_MISSING_DEFAULT))
        if value is not CONFIG_MISSING_DEFAULT:
            return value

        default_value = t.cast(ConfigValue, get_safe(self.defaults, key, sep=sep, default=CONFIG_MISSING_DEFAULT))
        if default_value is not CONFIG_MISSING_DEFAULT:
            return default_value

        return None


class SetConfigMixin:
    def set(self: ConfigMixinHost, key: str, value: object, *, sep: str = '>') -> None:
        default_value = t.cast(ConfigValue, get_safe(self.defaults, key, sep=sep, default=CONFIG_MISSING_DEFAULT))
        value = convert_value(value, default_value)

        normalized_default = convert_value(None, default_value)
        if value == normalized_default:
            del_safe(self.data, key, sep=sep)
            logger.debug(f'Resetted default to \'{key.replace(sep, ' > ')}\'')
            return

        set_safe(self.data, key, t.cast(ConfigValue, value), sep=sep)
        logger.debug(f'Setted \'{value}\' ({type(value).__name__}) to \'{key.replace(sep, ' > ')}\'')


class SaveConfigMixin:
    def _iter_ordered_items(self, data: ConfigMap, defaults: ConfigMap | None = None) -> cabc.Iterator[tuple[str, ConfigValue]]:
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
                new_data.append(f'{indent_prefix}{key}')
                new_data.extend(
                    self.dump_dict(
                        value,
                        child_defaults if isinstance(child_defaults, dict) else None,
                        indent + 1,
                    )
                )
            else:
                if type(value) is bool:
                    value = 'Yes' if value else 'No'
                new_data.append(f'{indent_prefix}{key}: {value}')
        return new_data

    def save(self: ConfigMixinHost) -> None:
        FS.ensure_dir(PATH_CONFIGS)
        text = '\n'.join(self.dump_dict(self.data, self.defaults))

        with self.save_lock:
            temp_file_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=self.path.parent,
                    prefix=f'{self.path.stem}.',
                    suffix='.tmp',
                    mode='w',
                    encoding='utf-8',
                    delete=False,
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
                        logger.warning(f'Can\'t replace {temp_file_path} with {self.path}. Try: #{tries}')
                        if attempt >= CONFIG_SAVE_RETRY_COUNT - 1:
                            raise
                        time.sleep(CONFIG_SAVE_RETRY_DELAY_SEC * tries)
            finally:
                if temp_file_path is not None:
                    try:
                        FS.delete_file(temp_file_path)
                    except OSError:
                        pass
