from __future__ import annotations

from typing import cast

from PySide6.QtCore import Qt

import src.app.context as ctx
from src.translation.types import ComboBoxProtocol


def _resolve_translator(explicit: object | None = None) -> object | None:
    if explicit is not None:
        return explicit
    services = getattr(ctx, 'services', None)
    return getattr(services, 'translator', None)


def _translate(translator: object | None, key: str) -> str:
    tr = getattr(translator, 'tr', None)
    if callable(tr):
        try:
            return str(tr(key))
        except Exception:
            return key
    return key


class TranslatableMixin:
    def __init__(
        self,
        key: str,
        *args: object,
        translator: object | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._key = key
        self._translator = _resolve_translator(translator)
        self._translator_bound = False
        self._sync_translator_binding()

    def _sync_translator_binding(self) -> None:
        if self._translator_bound or self._translator is None:
            self._update_text()
            return
        language_changed = getattr(self._translator, 'language_changed', None)
        if language_changed is not None:
            try:
                language_changed.connect(self._update_text)
                self._translator_bound = True
            except Exception:
                pass
        self._update_text()

    def _update_text(self) -> None:
        setter = getattr(self, "setText", None)
        if callable(setter):
            setter(_translate(self._translator, self._key))


class TranslatableComboBoxMixin():
    def __init__(
        self,
        *args: object,
        translator: object | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._translator = _resolve_translator(translator)
        self._translator_bound = False
        self._sync_translator_binding()

    def _sync_translator_binding(self) -> None:
        if self._translator_bound or self._translator is None:
            return
        language_changed = getattr(self._translator, 'language_changed', None)
        if language_changed is not None:
            try:
                language_changed.connect(self._update_text)
                self._translator_bound = True
            except Exception:
                pass

    def add_item(self, item: str) -> None:
        combo = cast(ComboBoxProtocol, self)
        combo.addItem(_translate(self._translator, item), item)
        index = combo.count() - 1
        combo.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_text(self) -> None:
        combo = cast(ComboBoxProtocol, self)
        for i in range(combo.count()):
            key = combo.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(key, str):
                continue
            combo.setItemText(i, _translate(self._translator, key))
