from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.utils.qt import build_object_name

from .label import MTPlainLabel, MTLabel
from .icon import MTIcon
from .widget import MTWidget


class MTCounter(MTWidget):
    _OBJECT_NAME = 'Counter'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        icon_path: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTCounter._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self._build_ui(tr_key=tr_key, icon_path=icon_path)

    def _build_ui(
        self,
        *,
        tr_key: str = '',
        icon_path: str = '',
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._info_widget = MTWidget(obj_name=(obj_name, 'Info'))
        self._info_layout = create_layout(LayoutType.HBOX, self._info_widget)
        self._main_layout.addWidget(self._info_widget)
        
        self._info_label = MTLabel(tr_key=tr_key, obj_name=(obj_name, 'Info'))
        self._info_layout.addWidget(self._info_label)

        self._info_layout.addStretch()

        self._info_icon = MTIcon(source=icon_path, obj_name=(obj_name, 'Info'))
        self._info_layout.addWidget(self._info_icon)

        self._counter_label = MTPlainLabel(text='0', obj_name=(obj_name, 'Counter'))
        self._main_layout.addWidget(self._counter_label)

    def set_value(self, value: int) -> None:
        self._counter_label.setText(str(value))
