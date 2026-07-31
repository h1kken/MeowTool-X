from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTLabel

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxCookieCheckerPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(
            parent,
            config=config,
            obj_name=obj_name
        )

        self._layout = create_layout(LayoutType.VBOX, self)
        
        lbl = MTLabel(tr_key='CK_CHCKR', obj_name='Main_Roblox_Cookie_Checker_Title_Label')
        btn = MTButton(tr_key='CHCK', obj_name='Main_Roblox_Cookie_Checker_Start_Button')
        
        self._layout.addWidget(lbl)
        self._layout.addWidget(btn)