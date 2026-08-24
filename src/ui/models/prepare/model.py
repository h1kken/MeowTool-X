from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QModelIndex

from src.translation import TranslationKey as TrKey
from src.translation.mixins import TranslatableHeaderTableModelMixin

from ..base import TableItem, TableModel


@dataclass(slots=True)
class PrepareTableItem(TableItem):
    value: str | Path
    lines: int

    @classmethod
    def create(cls, value: str | Path, lines: int) -> PrepareTableItem:
        return cls(
            value=value,
            lines=lines,
        )


class PrepareTableModel(TranslatableHeaderTableModelMixin, TableModel[PrepareTableItem]):
    _COLUMN_COUNT = 4
    _TRS = (
        TrKey(key='#'),
        TrKey(key='DT'),
        TrKey(key='LNS'),
        TrKey(),
    )
    
    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent, trs=self._TRS)

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
