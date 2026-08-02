from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout

from .button import MTButton
from .label import MTPlainLabel
from .scroll_area import MTScrollArea
from .widget import MTWidget


_GROUP_SECTION_SPACER_HEIGHT = 8


class _MTListItem(MTButton):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str,
        value: str,
        obj_name: str,
    ) -> None:
        super().__init__(parent, checkable=True, obj_name=obj_name)
        self._value = value
        
        self.setText(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(1, max(1, hint.height()))

    def data(self, role: int) -> str | None:
        if role == Qt.ItemDataRole.UserRole:
            return self._value
        if role == Qt.ItemDataRole.DisplayRole:
            return self.text()
        return None


class MTList(MTScrollArea):
    currentItemChanged = Signal(object, object)
    itemPressed = Signal(object)
    itemClicked = Signal(object)

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent, obj_name=obj_name)
        self._content = MTWidget(obj_name=f'{obj_name}_Content')
        self._content_layout = create_layout(LayoutType.VBOX, self._content)
        self.setWidget(self._content)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._items: list[QWidget] = []
        self._current_item: _MTListItem | None = None

    def clear(self) -> None:
        previous = self._current_item
        self._current_item = None
        for item in self._items:
            self._content_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        if previous is not None:
            self.currentItemChanged.emit(None, previous)

    def add_item(self, text: str, value: str, *, obj_name: str = '') -> _MTListItem:
        item = _MTListItem(
            text=text,
            value=value,
            obj_name=obj_name or self._item_object_name(value),
            parent=self._content,
        )
        def emit_pressed() -> None:
            self.itemPressed.emit(item)

        def handle_clicked(_checked: bool = False) -> None:
            self._activate_item(item)

        item.pressed.connect(emit_pressed)
        item.clicked.connect(handle_clicked)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def add_header(self, text: str, *, obj_name: str = '') -> MTPlainLabel:
        item = MTPlainLabel(self._content, text=text, obj_name=obj_name or self._item_object_name(text, suffix='Header'))
        item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def add_spacer(self, height: int = _GROUP_SECTION_SPACER_HEIGHT) -> MTWidget:
        item = MTWidget(self._content)
        item.setFixedHeight(max(0, int(height)))
        item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def count(self) -> int:
        return len(self._items)

    def item(self, index: int) -> QWidget | None:
        if 0 <= int(index) < len(self._items):
            return self._items[int(index)]
        return None

    def row(self, item: QWidget | None) -> int:
        if item is None:
            return -1
        try:
            return self._items.index(item)
        except ValueError:
            return -1

    def currentValue(self) -> str | None:
        if self._current_item is None:
            return None

        value = self._current_item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def plainValues(self) -> list[str]:
        values: list[str] = []
        
        for item in self._items:
            if not isinstance(item, _MTListItem):
                return []

            value = item.data(Qt.ItemDataRole.UserRole)
            values.append(str(value) if value is not None else '')

        return values

    def setCurrentItem(self, item: _MTListItem | None) -> None:
        if item is not None and item not in self._items:
            item = None
        if self._current_item is item:
            if item is not None and not item.isChecked():
                item.setChecked(True)
            return

        previous = self._current_item
        if previous is not None:
            previous.setChecked(False)
        self._current_item = item
        if item is not None:
            item.setChecked(True)
        self.currentItemChanged.emit(item, previous)

    def setCurrentRow(self, index: int) -> None:
        item = self.item(index)
        self.setCurrentItem(item if isinstance(item, _MTListItem) else None)

    def setCurrentValue(self, value: str | None) -> None:
        if value is None:
            self.setCurrentItem(None)
            return
        for item in self._items:
            if isinstance(item, _MTListItem) and item.data(Qt.ItemDataRole.UserRole) == value:
                self.setCurrentItem(item)
                return
        self.setCurrentItem(None)

    def _activate_item(self, item: _MTListItem) -> None:
        self.setCurrentItem(item)
        self.itemClicked.emit(item)

    def _item_object_name(self, value: str, *, suffix: str = 'Item') -> str:
        base = self.objectName().strip() or type(self).__name__
        token = ''.join(char if char.isalnum() else '_' for char in str(value).strip())
        token = '_'.join(part for part in token.split('_') if part) or 'Empty'
        return f'{base}_{suffix}_{token}'
