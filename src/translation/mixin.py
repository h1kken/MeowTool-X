from typing import Protocol, cast, runtime_checkable

from PySide6.QtCore import Qt

from src.translation.manager import translator as t


class _TextWidget(Protocol):
    def setText(self, text: str) -> None: ...


class _ComboBoxWidget(Protocol):
    def addItem(self, text: str, user_data: object = ...) -> None: ...
    def count(self) -> int: ...
    def setItemData(self, index: int, value: object, role: int = ...) -> None: ...
    def itemData(self, index: int, role: int = ...) -> object | None: ...
    def setItemText(self, index: int, text: str) -> None: ...


@runtime_checkable
class _ComboBoxContentWidthWidget(_ComboBoxWidget, Protocol):
    def sync_content_width(self) -> None: ...


class TranslatableMixin:
    def __init__(self, key: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._key = key
        t.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        cast(_TextWidget, self).setText(t.tr(self._key))
        

class TranslatableComboBoxMixin:
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        t.language_changed.connect(self._update_items_text)

    def add_item(self, item: str) -> None:
        combo = cast(_ComboBoxWidget, self)
        combo.addItem(t.tr(item), item)
        index = combo.count() - 1
        combo.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_items_text(self) -> None:
        combo = cast(_ComboBoxWidget, self)
        for i in range(combo.count()):
            key = combo.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(key, str):
                continue
            combo.setItemText(i, t.tr(key))
        if isinstance(self, _ComboBoxContentWidthWidget):
            self.sync_content_width()
