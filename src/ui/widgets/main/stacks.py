from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy, QStackedWidget, QWidget


class MTInlineEditorStack(QStackedWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.currentChanged.connect(self.updateGeometry)

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.sizeHint() if current else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.minimumSizeHint() if current else super().minimumSizeHint()
