from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.pages.base import BasePage
from src.ui.widgets.common import MTLabel

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxAutoReggerPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(parent, config=config, obj_name=obj_name)

        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._label = MTLabel(tr_key='AT_RGGR', obj_name='Main_Roblox_Auto_Regger_Title_Label')
        self._main_layout.addWidget(self._label)
