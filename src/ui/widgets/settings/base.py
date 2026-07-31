from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.widgets.common import MTWidget

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTBaseSetting(MTWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        obj_name: str = '',
    ) -> None:
        super().__init__(parent, obj_name=obj_name)
        self._config = config
        self._cfg_key = cfg_key
