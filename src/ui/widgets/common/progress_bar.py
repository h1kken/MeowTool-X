from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QProgressBar

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.utils.qt import build_object_name

from .label import MTPlainLabel
from .widget import MTWidget


class MTProgressBar(QWidget):
    _OBJECT_NAME = 'Progress_Bar'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = ()
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTProgressBar._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._current_item_label = MTPlainLabel(obj_name=(obj_name, 'Current_Item'))
        self._main_layout.addWidget(self._current_item_label)
        
        self._bar_widget = QProgressBar()
        self._bar_widget.setObjectName(build_object_name((obj_name, 'Bar')))
        self._main_layout.addWidget(self._bar_widget)
        
        self._values_widget = MTWidget(obj_name=(obj_name, 'Values'))
        self._values_layout = create_layout(LayoutType.GRID, self._values_widget)
        self._main_layout.addWidget(self._values_widget)
        
        for column in range(3):
            self._values_layout.setColumnStretch(column, 1)
        
        self._start_value = MTPlainLabel(obj_name=(obj_name, 'Start_Value'))
        self._current_value = MTPlainLabel(obj_name=(obj_name, 'Current_Value'))
        self._end_value = MTPlainLabel(obj_name=(obj_name, 'End_Value'))
        
        for column, widget in enumerate((self._start_value, self._current_value, self._end_value)):
            self._values_layout.addWidget(widget, 0, column)

    def set_current_item(self, text: str) -> None:
        self._current_item_label.setText(text)

    def set_value(self, value: int) -> None:
        self._bar_widget.setValue(value)
        self._current_value.setText(str(value))

    def set_range(self, minimum: int, maximum: int) -> None:
        self._bar_widget.setRange(minimum, maximum)
        self._start_value.setText(str(minimum))
        self._end_value.setText(str(maximum))

    def reset(self) -> None:
        self._bar_widget.reset()
        self._current_item_label.clear()
        self._start_value.clear()
        self._current_value.clear()
        self._end_value.clear()
