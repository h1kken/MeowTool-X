
from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from src.ui.widgets.main.text import MTButton


class MTButtonSetting(MTButton):
    def __init__(
        self,
        action: Callable[[], None],
        tr_key: str,
        obj_name: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr_key=tr_key, obj_name=f"{obj_name}_Setting", parent=parent)
        self.setProperty("rainbowBorderTarget", True)
        self.clicked.connect(action)
