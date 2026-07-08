from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTButton, MTWidget


class SidebarCategory(MTWidget):
    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        obj_name: str = '',
    ) -> None:
        super().__init__(obj_name=f"{obj_name}_Category_Widget", parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._main_layout = create_layout(LayoutType.VBOX, parent=self)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._header_button = MTButton(tr_key="", parent=self, obj_name=f"{obj_name}_Category_Header_Button")
        self._header_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._content_widget = MTWidget(self, obj_name=f"{obj_name}_Category_Content_Widget")
        self._content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._content_layout = create_layout(LayoutType.VBOX, parent=self._content_widget)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._main_layout.addWidget(self._header_button)
        self._main_layout.addWidget(self._content_widget)

    def add_button(self, button: QWidget) -> None:
        self._content_layout.addWidget(button)
        self.updateGeometry()

    def header_button(self) -> MTButton:
        return self._header_button

