from __future__ import annotations

import typing as t
import collections.abc as cabc

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common.widget import MTWidget

from .button import MTButton
from .scroll_area import MTScrollArea


class MTListItem(MTButton):
    clickedItem = Signal(object)

    _OBJECT_NAME = 'Item'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str,
        value: str,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, checkable=True, obj_name=(*obj_name, MTListItem._OBJECT_NAME))
        self.setText(text)
        self.setProperty('name', text)

        self._value = value
        
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.clicked.connect(lambda: self.clickedItem.emit(self))

    @property
    def value(self) -> str:
        return self._value


class MTList(MTScrollArea):
    currentItemChanged = Signal(object, object)

    _OBJECT_NAME = 'List'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, MTList._OBJECT_NAME))

        self._items: list[MTListItem] = []
        self._current_item: MTListItem | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._content = MTWidget(obj_name=(obj_name, 'Content'))
        self._content_layout = create_layout(LayoutType.VBOX, self._content)
        self.setWidget(self._content)
        
    @property
    def currentItem(self) -> MTListItem | None:
        return self._current_item

    @property
    def currentText(self) -> str | None:
        return self._current_item.text() if self._current_item is not None else None

    @property
    def currentValue(self) -> str | None:
        return self._current_item.value if self._current_item is not None else None

    def _on_item_clicked(self, item: MTListItem) -> None:
        self.setCurrentItem(item)

    def addItem(self, text: str, value: str, *, sort: bool = False) -> MTListItem:
        item = MTListItem(self._content, text=text, value=value)
        item.clickedItem.connect(self._on_item_clicked)
        
        self._items.append(item)
        self._content_layout.addWidget(item)
        
        if sort:
            self.sortItems(key=lambda item: item.text().casefold())
        
        return item
    
    def removeItem(self, item: MTListItem) -> None:
        if item not in self._items:
            return

        if item is self._current_item:
            self.setCurrentItem(None)

        self._items.remove(item)
        self._content_layout.removeWidget(item)
        item.deleteLater()
        
    def setItems(self, items: t.Sequence[tuple[str, str]]) -> None:
        old_names = {item.value: item for item in self._items}
        new_names = {value: text for text, value in items}
        
        for value, text in new_names.items():
            item = old_names.pop(value, None)
            
            if item is not None:
                self._content_layout.addWidget(item)
            else:
                self.addItem(text, value)
        
        for item in old_names.values():
            self.removeItem(item)
    
    def sortItems(self, *, key: cabc.Callable[[MTListItem], t.Any], reverse: bool = False) -> None:
        self._items.sort(key=key, reverse=reverse)

        for item in self._items:
            self._content_layout.addWidget(item)
    
    def clear(self) -> None:
        for item in self._items:
            self._content_layout.removeWidget(item)
            item.deleteLater()

        self._items.clear()
        self.setCurrentItem(None)
    
    def setCurrentItem(self, item: MTListItem | None) -> None:
        if self._current_item is item:
            return

        previous = self._current_item
        if previous:
            previous.setChecked(False)

        self._current_item = item
        if item:
            item.setChecked(True)

        self.currentItemChanged.emit(item, previous)
