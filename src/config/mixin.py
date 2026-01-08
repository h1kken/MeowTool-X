from typing import Optional, Any
from src.utils.filesystem import create_folder, get_safe, set_safe
from src.utils.consts import PATH_CONFIGS
from src.utils.logging import logger


class GetConfigMixin:
    def get(self, key: str, *, sep: str = '>', default: Optional[Any] = None):
        value = get_safe(self._data, key, sep=sep, default=default)
        logger.debug(f'Loaded \'{value}\' from \'{key.replace(sep, ' > ')}\'')
        return value


class SetConfigMixin:
    def set(self, key: str, value: Any, *, sep: str = '>'):
        set_safe(self._data, key, value, sep=sep)
        logger.debug(f'Setted \'{value}\' to \'{key.replace(sep, ' > ')}\'')


class SaveConfigMixin:
    def _dump_dict(self, old_data: dict, indent: int = 0):
        new_data = []
        for key, value in old_data.items():
            if isinstance(value, dict):
                new_data.append(f'{'\t' * indent}{key}')
                new_data.extend(self._dump_dict(value, indent + 1))
            else:
                if type(value) is bool:
                    value = 'Yes' if value else 'No'
                new_data.append(f'{'\t' * indent}{key}: {value}')
        return new_data
    
    def save(self):
        create_folder(PATH_CONFIGS)
        lines = self._dump_dict(self._data)
        with open(self._path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        logger.debug(f'Config \'{self._path.stem}\' is saved')
