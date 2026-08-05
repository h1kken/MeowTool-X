from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from src.translation.mixins import TranslatableMixin
from src.utils.qt import build_object_name


class MTPlainLabel(QLabel):
    _OBJECT_NAME = 'PlainLabel'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str = '',
        obj_name: tuple[str, ...] = ()
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class MTLabel(TranslatableMixin, QLabel):
    _OBJECT_NAME = 'Label'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, tr_key=tr_key)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
