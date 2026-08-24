import typing as t

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView, QWidget 

from src.ui.models.base import TableModel
from src.utils.qt import build_object_name


class MTTable(QTableView):
    _OBJECT_NAME = 'Table'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        model: TableModel[t.Any] | None = None,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTTable._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setModel(model)
