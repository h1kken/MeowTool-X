from __future__ import annotations

import collections.abc as cabc

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtGui import QIcon

from src.translation.mixins import TranslatableMixin
from src.utils.qt import build_object_name


class MTButton(TranslatableMixin, QPushButton):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
        checkable: bool = False,
        checked: bool = False,
        action: cabc.Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, tr_key=tr_key)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName(build_object_name((*obj_name, 'Button')))

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if action is not None:
            self.clicked.connect(action)

        self._icon_state: dict[str, object] | None = None

    def set_icon(
        self,
        source: str | None,
        *,
        align: str = 'left',
        size: QSize | None = None,
        spacing: float = 3.0,
    ) -> None:
        icon = QIcon(source) if source is not None else QIcon()
        icon_size = size if size is not None and not size.isEmpty() else QSize(16, 16)
        
        if not icon.isNull():
            actual = icon.actualSize(icon_size)
            if actual.isValid() and not actual.isEmpty():
                icon_size = actual

        self.setIcon(icon)
        self.setIconSize(icon_size)

        self._icon_state = {
            'source': source,
            'align': align,
            'size': icon_size,
            'spacing': max(0.0, float(spacing)),
        }
