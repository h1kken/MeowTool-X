from __future__ import annotations

import collections.abc as cabc

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from PySide6.QtCore import Qt, QObject, QModelIndex, QAbstractTableModel

from src.translation.mixins import TranslatableHeaderTableModelMixin


@dataclass(slots=True)
class PrepareTableItem:
    id: UUID
    value: str | Path
    lines: int

    @classmethod
    def create(cls, value: str | Path, lines: int) -> PrepareTableItem:
        return cls(
            id=uuid4(),
            value=value,
            lines=lines,
        )


class PrepareTableModel(TranslatableHeaderTableModelMixin, QAbstractTableModel):
    _COLUMN_COUNT = 4
    _TR_KEYS = ('#', 'DT', 'LNS', '')
    
    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent, tr_keys=PrepareTableModel._TR_KEYS)
    
        self._items: list[PrepareTableItem] = []
    
    @property
    def items(self) -> cabc.Sequence[PrepareTableItem]:
        return self._items
    
    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int: # type: ignore[override]
        return len(self._items)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int: # type: ignore[override]
        return PrepareTableModel._COLUMN_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object | None: # type: ignore[override]
        if not index.isValid():
            return
        if role != Qt.ItemDataRole.DisplayRole:
            return

        item = self._items[index.row()]

        match index.column():
            case 0: return index.row() + 1
            case 1: return str(item.value)
            case 2: return item.lines
            case _: pass
    
    def add_item(self, item: PrepareTableItem):
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()
    
    def remove_item(self, item_id: UUID) -> None:
        row = next((row for row, item in enumerate(self._items) if item.id == item_id), None)
        if row is None:
            return

        self.beginRemoveRows(QModelIndex(), row, row)
        self._items.pop(row)
        self.endRemoveRows()

    def clear(self) -> None:
        if not self._items:
            return
    
        self.beginRemoveRows(QModelIndex(), 0, len(self._items) - 1)
        self._items.clear()
        self.endRemoveRows()
