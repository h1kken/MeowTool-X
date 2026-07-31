from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QFrame, QScrollArea


class MTScrollArea(QScrollArea):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(20)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setStyleSheet('background: transparent; border: 0;')

        if obj_name:
            self.setObjectName(obj_name)
