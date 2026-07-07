from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from src.translation.manager import TranslationManager
from src.translation.mixin import TranslatableMixin
from src.ui.widgets.main.box import BoxThemeMixin


class MTPlainLabel(BoxThemeMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)
        self.init_box_theme()

        if obj_name:
            self.setObjectName(obj_name)


class MTLabel(BoxThemeMixin, TranslatableMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(
        self,
        tr_key: str,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
        translator: TranslationManager | None = None,
    ) -> None:
        super().__init__(tr_key, parent, translator=translator)
        self.init_box_theme()
        self._sync_translator_binding()

        if obj_name:
            self.setObjectName(obj_name)


class MTButton(BoxThemeMixin, TranslatableMixin, QPushButton):
    PAINTED_BOX_THEME = False

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        tr_key: str = '',
        obj_name: str = '',
        translator: TranslationManager | None = None,
        checkable: bool = False,
        checked: bool = False,
    ) -> None:
        super().__init__(tr_key, parent, translator=translator)
        self.setFlat(True)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_box_theme()
        self._text_icon_state: dict[str, object] | None = None
        self._default_text_icon_state: dict[str, object] | None = None
        self._default_text_icon_captured = False
        self._sync_translator_binding()

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if obj_name:
            self.setObjectName(obj_name)

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

    def clear_text_icon(self) -> None:
        self.setIcon(QIcon())
        self._text_icon_state = None
        self.updateGeometry()
        self.update()

    def text_icon_state(self) -> dict[str, object] | None:
        return self._clone_icon_state(self._text_icon_state)

    def default_text_icon_state(self) -> dict[str, object] | None:
        return self._clone_icon_state(self._default_text_icon_state)

    def capture_default_text_icon_state(self) -> None:
        if self._default_text_icon_captured:
            return
        self._default_text_icon_state = self.text_icon_state()
        self._default_text_icon_captured = True

    def restore_default_text_icon_state(self) -> None:
        self.restore_text_icon_state(self._default_text_icon_state)

    def restore_text_icon_state(self, state: dict[str, object] | None) -> None:
        cloned = self._clone_icon_state(state)
        if cloned is None:
            self.clear_text_icon()
            return

        source = str(cloned.get('source', '')).strip()
        size = cloned.get('size')
        raw_spacing = cloned.get('spacing', 0.0)
        spacing = float(raw_spacing) if isinstance(raw_spacing, (int, float)) else 0.0
        self.set_text_icon(
            source=source,
            align=str(cloned.get('align', 'left')),
            size=size if isinstance(size, QSize) else None,
            spacing=spacing,
        )

    def set_text_icon_color(self, value: QColor | str) -> bool:
        _ = value
        return False

    def _clone_icon_state(self, state: dict[str, object] | None) -> dict[str, object] | None:
        if state is None:
            return None

        raw_spacing = state.get('spacing', 0.0)
        spacing = float(raw_spacing) if isinstance(raw_spacing, (int, float)) else 0.0
        size = state.get('size')
        return {
            'source': str(state.get('source', '')),
            'align': str(state.get('align', 'left')),
            'spacing': spacing,
            'size': QSize(size) if isinstance(size, QSize) and size.isValid() else QSize(),
        }


__all__ = ('MTButton', 'MTLabel', 'MTPlainLabel')
