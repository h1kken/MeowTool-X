from dataclasses import dataclass, field
import typing as t
import collections.abc as cabc

from uuid import UUID, uuid4

from PySide6.QtCore import QModelIndex, Signal, QAbstractTableModel
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.translation.mixins import TranslatableHeaderTableModelMixin


@dataclass(slots=True)
class TableItem:
    id: UUID = field(default_factory=uuid4, init=False)


TItem = t.TypeVar("TItem", bound=TableItem)


class TableModel(TranslatableHeaderTableModelMixin, QAbstractTableModel, t.Generic[TItem]):
    itemAdded = Signal(TableItem)
    itemRemoved = Signal(TableItem)
    
    _TRS: tuple[TrKey, ...]
    
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, trs=self._TRS)
        
        self._items: list[TItem] = []
    
    @property
    def items(self) -> cabc.Sequence[TItem]:
        return self._items
    
    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int: # type: ignore[override]
        return len(self._items)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int: # type: ignore[override]
        return len(self._TRS)

    def item_at(self, row: int) -> TItem | None:
        if not (0 <= row < len(self._items)):
            return
        return self._items[row]
    
    def add_item(self, item: TItem):
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()
        
        self.itemAdded.emit(item)
    
    def remove_item(self, item_id: UUID) -> None:
        row = next((row for row, item in enumerate(self._items) if item.id == item_id), None)
        if row is None:
            return

        self.beginRemoveRows(QModelIndex(), row, row)
        item = self._items.pop(row)
        self.endRemoveRows()
        
        self.itemRemoved.emit(item)

    def clear(self) -> None:
        if not self._items:
            return
    
        self.beginRemoveRows(QModelIndex(), 0, len(self._items) - 1)
        self._items.clear()
        self.endRemoveRows()
