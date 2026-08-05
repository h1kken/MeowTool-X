from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

import src.app.context as ctx
translator = ctx.services.translator


class TranslatableMixin:
    def __init__(
        self,
        parent: QWidget | None = None,
        *args: object,
        tr_key: str = '',
        **kwargs: object,
    ) -> None:
        super().__init__(parent, *args, **kwargs) # type: ignore
        self._tr_key = tr_key
        
        translator.languageChanged.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        setter = getattr(self, 'setText', None)
        if callable(setter):
            setter(translator.tr(self._tr_key))


class _ComboBoxProtocol(t.Protocol):
    def addItem(self, text: str, user_data: object = ...) -> None: ...
    def count(self) -> int: ...
    def setItemData(self, index: int, value: object, role: int = ...) -> None: ...
    def itemData(self, index: int, role: int = ...) -> object | None: ...
    def setItemText(self, index: int, text: str) -> None: ...


class TranslatableComboBoxMixin:
    def __init__(
        self,
        parent: QWidget | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, *args, **kwargs) # type: ignore

        translator.languageChanged.connect(self._update_text)

    def add_item(self, item: str) -> None:
        combo = t.cast(_ComboBoxProtocol, self)
        combo.addItem(translator.tr(item), item)
        index = combo.count() - 1
        combo.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_text(self) -> None:
        combo = t.cast(_ComboBoxProtocol, self)
        for i in range(combo.count()):
            tr_key = combo.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(tr_key, str):
                continue
            combo.setItemText(i, translator.tr(tr_key))
