from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTLabel

if t.TYPE_CHECKING:
    from src.config import Config

class RobloxCookieRefresherPage(BasePage):
    _OBJECT_NAME = 'Roblox_Cookie_Refresher'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, self._OBJECT_NAME))

        self._build_ui(obj_name=(*obj_name, self._OBJECT_NAME))

    def _build_ui(
        self,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._label = MTLabel(tr_key='CK_RFRSHR', obj_name=(*obj_name, 'Title'))
        self._main_layout.addWidget(self._label)

        self._button = MTButton(tr_key='RFRSH', obj_name=(*obj_name, 'Start'))
        self._main_layout.addWidget(self._button)
