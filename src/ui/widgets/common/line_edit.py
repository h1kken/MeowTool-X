from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLineEdit


class MTLineEdit(QLineEdit):
    def __init__(
        self,
        text: str = '',
        obj_name: str = '',
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrame(False)
        self.setTextMargins(0, 0, 0, 0)
        
        if obj_name:
            self.setObjectName(obj_name)
            
        self._placeholder_tr_key: str | None = None
