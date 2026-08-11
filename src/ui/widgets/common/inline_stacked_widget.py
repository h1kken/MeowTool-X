from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QStackedWidget, QWidget

from src.utils.qt import build_object_name


class MTInlineStackedWidget(QStackedWidget):
    _OBJECT_NAME = 'Inline_Stacked_Widget'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTInlineStackedWidget._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.currentChanged.connect(self.updateGeometry)

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.sizeHint() if current else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.minimumSizeHint() if current else super().minimumSizeHint()
