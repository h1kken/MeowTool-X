from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTLabel

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxLogPassCheckerPage(BasePage):
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
        
        lbl = MTLabel(tr_key='LP_CHCKR', obj_name='Main_Roblox_LogPass_Checker_Title_Label')
        
        self._layout.addWidget(lbl)
