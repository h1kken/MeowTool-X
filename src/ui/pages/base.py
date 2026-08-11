from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.widgets.common import MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


class BasePage(MTWidget):
    _OBJECT_NAME = 'Page'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, BasePage._OBJECT_NAME))
        self._config = config
