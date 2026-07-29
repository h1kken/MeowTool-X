from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QAbstractButton, QWidget

from src.translation.mixin import TranslatableMixin


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
        super().__init__(tr_key, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)

class MTButton(TranslatableMixin, QAbstractButton):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: str = '',
        checkable: bool = False,
        checked: bool = False,
    ) -> None:
        super().__init__(tr_key, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if obj_name:
            self.setObjectName(obj_name)

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


__all__ = (
    'MTButton',
    'MTLabel',
    'MTPlainLabel',
)
