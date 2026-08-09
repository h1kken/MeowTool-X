from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget, QWidget

from src.utils.qt import build_object_name


class MTStackedWidget(QStackedWidget):
    _OBJECT_NAME = 'Stacked_Widget'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
