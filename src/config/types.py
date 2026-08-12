import typing as t

import threading
from pathlib import Path

from src.core.types import DataMap


type SortCategoryKind = t.Literal['none', 'text', 'number']


class ConfigMixinHost(t.Protocol):
    @property
    def path(self) -> Path: ...
    
    @property
    def data(self) -> DataMap: ...

    @property
    def defaults(self) -> DataMap: ...

    @property
    def save_lock(self) -> threading.Lock: ...

    def dump_dict(self, old_data: DataMap, defaults: DataMap | None = None, indent: int = 0) -> list[str]: ...


__all__ = (
    'DataMap',
    'ConfigScalar',
    'DataValue',
    'SortCategoryKind',
)
