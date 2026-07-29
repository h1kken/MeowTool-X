
from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from src.ui.widgets.main.text import MTButton


class MTButtonSetting(MTButton):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: str = '',
        action: Callable[[], None],
    ) -> None:
        super().__init__(parent, tr_key=tr_key, obj_name=f'{obj_name}_Setting')
        self.clicked.connect(action)
