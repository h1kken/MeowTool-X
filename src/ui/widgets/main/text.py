from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QLabel, QAbstractButton, QWidget

from src.translation.mixin import TranslatableMixin
from src.ui.widgets.main.box import BoxThemeMixin


class MTPlainLabel(BoxThemeMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)

        if obj_name:
            self.setObjectName(obj_name)

        self.init_box_theme()


class MTLabel(BoxThemeMixin, TranslatableMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(
        self,
        tr_key: str = '',
        obj_name: str = '',
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr_key, parent)

        if obj_name:
            self.setObjectName(obj_name)

        self.init_box_theme()
        

class MTButton(BoxThemeMixin, TranslatableMixin, QAbstractButton):
    PAINTED_BOX_THEME = False

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        tr_key: str = '',
        obj_name: str = '',
        checkable: bool = False,
        checked: bool = False,
    ) -> None:
        super().__init__(tr_key, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if obj_name:
            self.setObjectName(obj_name)
            
        self.init_box_theme()
        self._text_icon_state: dict[str, object] | None = None
        self._default_text_icon_state: dict[str, object] | None = None
        self._default_text_icon_captured = False

    def set_text_icon(
        self,
        *,
        source: str,
        align: str = 'left',
        size: QSize | None = None,
        spacing: float = 4.0,
        color: QColor | None = None,
    ) -> bool:
        _ = color
        icon = QIcon(str(source))
        if icon.isNull():
            return False

        fallback = QSize(16, 16)
        if isinstance(size, QSize) and size.isValid() and not size.isEmpty():
            icon_size = QSize(size)
        else:
            actual = icon.actualSize(fallback)
            icon_size = actual if actual.isValid() and not actual.isEmpty() else QSize(fallback)
        self.setIcon(icon)
        self.setIconSize(icon_size)
        self._text_icon_state = {
            'source': str(source),
            'align': str(align or 'left'),
            'size': QSize(icon_size),
            'spacing': max(0.0, float(spacing)),
        }
        self.updateGeometry()
        self.update()
        return True


__all__ = ('MTButton', 'MTLabel', 'MTPlainLabel')
