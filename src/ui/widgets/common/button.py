from __future__ import annotations

import collections.abc as cabc

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QPushButton

from src.translation import TranslationKey as TrKey
from src.translation.mixins import TranslatableMixin
from src.utils.qt import build_object_name


class MTPlainButton(QPushButton):
    _OBJECT_NAME = 'PlainButton'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str = '',
        obj_name: tuple[str, ...] = (),
        checkable: bool = False,
        checked: bool = False,
        action: cabc.Callable[[], None] | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(build_object_name((*obj_name, MTPlainButton._OBJECT_NAME)))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if action is not None:
            self.clicked.connect(action)


class MTButton(TranslatableMixin, QPushButton):
    _OBJECT_NAME = 'Button'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
        checkable: bool = False,
        checked: bool = False,
        action: cabc.Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, tr=tr)
        self.setObjectName(build_object_name((*obj_name, MTButton._OBJECT_NAME)))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if action is not None:
            self.clicked.connect(action)
