from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey

from ..base import TableItem, TableModel


@dataclass(slots=True)
class ThreadsTableItem(TableItem):
    value: str | Path
    lines: int


class ThreadsTableModel(TableModel[ThreadsTableItem]):
    _TRS = (
        TrKey(key='THRD'),
        TrKey(key='DT'),
        TrKey(key='LNS'),
    )
    
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

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
