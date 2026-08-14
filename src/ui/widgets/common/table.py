from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableView, QWidget 

from src.utils.qt import build_object_name


class MTTable(QTableView):
    _OBJECT_NAME = 'Table'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTTable._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
