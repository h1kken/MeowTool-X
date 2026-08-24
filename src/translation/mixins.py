from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, QObject, QAbstractItemModel
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
import src.app.context as ctx
translator = ctx.services.translator

if t.TYPE_CHECKING:
    from src.ui.widgets.types import ComboItem


class TranslatableMixin:
    def __init__(
        self,
        parent: QWidget | None = None,
        *args: object,
        tr: TrKey = TrKey(),
        **kwargs: object,
    ) -> None:
        super().__init__(parent, *args, **kwargs) # type: ignore
        self._tr = tr
        
        translator.languageChanged.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        setter = getattr(self, 'setText', None)
        if callable(setter):
            setter(f'{self._tr.prefix}{translator.tr(self._tr.key)}{self._tr.suffix}')


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

    def add_item(self, item: ComboItem) -> None:
        combo = t.cast(_ComboBoxProtocol, self)
        combo.addItem(translator.tr(item.tr.key), item.tr.key)

    def add_items(self, items: list[ComboItem]) -> None:
        for item in items:
            self.add_item(item)

    def _update_text(self) -> None:
        combo = t.cast(_ComboBoxProtocol, self)
        
        for i in range(combo.count()):
            tr_key = combo.itemData(i, Qt.ItemDataRole.UserRole)
            if not isinstance(tr_key, str):
                continue
            
            combo.setItemText(i, translator.tr(tr_key))


class TranslatableHeaderTableModelMixin:
    def __init__(
        self,
        parent: QObject | None = None,
        *args: object,
        trs: tuple[TrKey, ...] = (),
        **kwargs: object,
    ) -> None:
        super().__init__(parent, *args, **kwargs)  # type: ignore
        self._trs = trs

        translator.languageChanged.connect(self._update_headers)

    def _update_headers(self) -> None:
        model = t.cast(QAbstractItemModel, self)
        model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(self._trs) - 1)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return
        if orientation != Qt.Orientation.Horizontal:
            return
        if not 0 <= section < len(self._trs):
            return
        
        tr = self._trs[section]
        return f'{tr.prefix}{translator.tr(tr.key)}{tr.suffix}'
