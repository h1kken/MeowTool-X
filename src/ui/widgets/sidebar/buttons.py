from PySide6.QtWidgets import QWidget

from src.ui.widgets.main.text import MTButton


class MTSidebarButton(MTButton):
    def __init__(self, *, parent: QWidget | None = None, tr_key: str = '', obj_name: str = '') -> None:
        super().__init__(parent=parent, tr_key=tr_key, obj_name=obj_name)

    def setText(self, text: str) -> None:
        super().setText(text)
        self.updateGeometry()
        self.update()
