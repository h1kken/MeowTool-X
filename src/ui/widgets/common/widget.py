from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from src.utils.qt import build_object_name


class MTWidget(QWidget):
    _OBJECT_NAME = 'Widget'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name(obj_name)) # (*obj_name, self._OBJECT_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
