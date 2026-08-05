from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLineEdit

from src.utils.qt import build_object_name


class MTLineEdit(QLineEdit):
    _OBJECT_NAME = 'LineEdit'
    
    def __init__(
        self,
        text: str = '',
        obj_name: tuple[str, ...] = (),
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
