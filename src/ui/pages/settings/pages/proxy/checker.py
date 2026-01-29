from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from src.ui.widgets import MTWidget
from src.ui.layouts.factory import LayoutType, create_layout


class SettingsProxyCheckerPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name='Settings_Proxy_Checker_Page_Widget')
        main_layout.addWidget(main_widget, alignment=Qt.AlignmentFlag.AlignTop)
        # TODO