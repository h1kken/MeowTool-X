from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from src.translation.mixins import TranslatableMixin


class MTPlainLabel(QLabel):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str = '',
        obj_name: str = ''
    ) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)


class MTLabel(TranslatableMixin, QLabel):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: str = '',
    ) -> None:
        super().__init__(parent, tr_key=tr_key)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)
