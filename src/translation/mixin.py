from __future__ import annotations

from typing import cast, Protocol

from PySide6.QtCore import Qt

import src.app.context as ctx
translator = ctx.services.translator


class TranslatableMixin:
    def __init__(self, key: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._key = key
        
        translator.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        setter = getattr(self, "setText", None)
        if callable(setter):
            setter(translator.tr(self._key))


class _ComboBoxProtocol(Protocol):
    def addItem(self, text: str, user_data: object = ...) -> None: ...
    def count(self) -> int: ...
    def setItemData(self, index: int, value: object, role: int = ...) -> None: ...
    def itemData(self, index: int, role: int = ...) -> object | None: ...
    def setItemText(self, index: int, text: str) -> None: ...


class TranslatableComboBoxMixin():
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        translator.language_changed.connect(self._update_text)

    def add_item(self, item: str) -> None:
        combo = cast(_ComboBoxProtocol, self)
        combo.addItem(translator.tr(item), item)
        index = combo.count() - 1
        combo.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_text(self) -> None:
        combo = cast(_ComboBoxProtocol, self)
        for i in range(combo.count()):
            key = combo.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(key, str):
                continue
            combo.setItemText(i, translator.tr(key))
