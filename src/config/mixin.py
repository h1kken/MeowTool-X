from typing import Optional, Any
from src.utils.file_utils import get_nested, set_nested


class GetConfigMixin:
    def get(self, key: str, *, sep: str = '>', default: Optional[Any] = None):
        return get_nested(self._data, key, sep=sep, default=default)


class SetConfigMixin:
    def set(self, key: str, value: Any, *, sep: str = '>'):
        set_nested(self._data, key, value, sep=sep)
            
            
class SaveConfigMixin:
    def _dump_dict(self, data: dict, indent: int = 0):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{'\t' * indent}{key}')
                lines.extend(self._dump_dict(value, indent + 1))
            else:
                if type(value) is bool:
                    value = 'Yes' if value else 'No'
                lines.append(f'{'\t' * indent}{key}: {value}')
        return lines
    
    def save(self):
        lines = self._dump_dict(self._data)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))