import threading
from pathlib import Path
import typing as t

type ConfigScalar = None | bool | int | float | str
type ConfigValue = (
    ConfigScalar
    | list['ConfigValue']
    | tuple['ConfigValue', ...]
    | dict[str, 'ConfigValue']
)
ConfigMap: t.TypeAlias = dict[str, ConfigValue]
type SortCategoryKind = t.Literal['none', 'text', 'number']


class ConfigMixinHost(t.Protocol):
    @property
    def name(self) -> str: ...
    
    @property
    def path(self) -> Path: ...
    
    @property
    def data(self) -> ConfigMap: ...

    @property
    def defaults(self) -> ConfigMap: ...

    @property
    def save_lock(self) -> threading.Lock: ...

    def dump_dict(self, old_data: ConfigMap, defaults: ConfigMap | None = None, indent: int = 0) -> list[str]: ...


__all__ = (
    'ConfigMap',
    'ConfigMixinHost',
    'ConfigScalar',
    'ConfigValue',
    'SortCategoryKind',
)
