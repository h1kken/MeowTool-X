from pathlib import Path
from ..utils.file_utils import get_nested, set_nested


class GetConfigMixin:
    def get(self, key, *, sep='>', default=None):
        self._data: dict
        return get_nested(self._data, key, sep=sep, default=default)


class SetConfigMixin:
    def set(self, key, value, *, sep='>'):
        self._data: dict
        set_nested(self._data, key, value, sep=sep)
            
            
class SaveConfigMixin:
    def _dump_dict(self, data: dict, indent: int = 0):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{'\t' * indent}{key}')
                lines.extend(self._dump_dict(value, indent + 1))
            else:
                lines.append(f'{'\t' * indent}{key}: {value}')
        return lines
    
    def save(self):
        self._data: dict
        self._path: Path
        lines = self._dump_dict(self._data)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))