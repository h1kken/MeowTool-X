from typing import Optional, Any
from src.utils.file_utils import get_nested, set_nested
from src.utils.consts import PATH_CONFIGS
from src.utils.file_utils import create_folder


class GetConfigMixin:
    def get(self, key: str, *, sep: str = '>', default: Optional[Any] = None):
        return get_nested(self._data, key, sep=sep, default=default)


class SetConfigMixin:
    def set(self, key: str, value: Any, *, sep: str = '>'):
        set_nested(self._data, key, value, sep=sep)


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