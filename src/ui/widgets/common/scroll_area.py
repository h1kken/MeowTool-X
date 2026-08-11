from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QScrollArea

from src.utils.qt import build_object_name


class MTScrollArea(QScrollArea):
    _OBJECT_NAME = 'ScrollArea'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, widgetResizable=True)
        self.setObjectName(build_object_name((*obj_name, MTScrollArea._OBJECT_NAME)))
        self.viewport().setObjectName(build_object_name((*obj_name, MTScrollArea._OBJECT_NAME, 'Viewport')))
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(20)
