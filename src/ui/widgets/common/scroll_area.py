from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QScrollArea

from src.utils.qt import build_object_name


class MTScrollArea(QScrollArea):
    _OBJECT_NAME = 'ScrollArea'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        resizable: bool = True,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, widgetResizable=resizable)
        self.setObjectName(build_object_name((*obj_name, MTScrollArea._OBJECT_NAME)))
        self.viewport().setObjectName(build_object_name((*obj_name, MTScrollArea._OBJECT_NAME, 'Viewport')))
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(20)

    def sizeHint(self) -> QSize:
        widget = self.widget()
        if widget is None:
            return QSize(0, 0)

        size = widget.sizeHint()
        frame = self.frameWidth() * 2
        
        return QSize(size.width() + frame, size.height() + frame)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self.sizeHint().height())
