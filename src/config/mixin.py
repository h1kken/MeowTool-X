import json
from ..utils.helpers import get_nested, set_nested


class GetConfigMixin:
    def get(self, key, *, sep='.', default=None):
        return get_nested(self._data, key, sep=sep, default=default)


class SetConfigMixin:
    def set(self, key, value, *, sep='.'):
        set_nested(self._data, key, value, sep=sep)
            
            
class SaveConfigMixin:
    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)