from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.widgets.common import MTWidget

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader

T = t.TypeVar('T')


class MTBaseSetting(MTWidget, t.Generic[T]): # static type
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        type_: type[T], # runtime type
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, 'Setting'))
        self._config = config
        self._cfg_key = cfg_key
        self._type = type_

    @property
    def value(self) -> T:
        return self._config.get(self._cfg_key, self._type)
    
    @value.setter
    def value(self, value: T) -> None:
        self._config.set(self._cfg_key, value)
