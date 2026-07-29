from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.widgets.main.containers import MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


class BasePage(MTWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ) -> None:
        super().__init__(parent=parent, obj_name=obj_name)
        self._config = config
