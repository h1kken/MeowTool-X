from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxCookieCheckerPage(BasePage):
    _OBJECT_NAME = 'Roblox_Cookie_Checker'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, self._OBJECT_NAME))

        self._build_ui()

    def _build_ui(self) -> None:
        # obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
