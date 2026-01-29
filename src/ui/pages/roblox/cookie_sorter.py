from PySide6.QtWidgets import QWidget
from src.ui.widgets import MTLabel, MTButton
from src.services.roblox import RobloxCookieSorter
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class RobloxCookieSorterPage(QWidget):
    def __init__(self):
        super().__init__()
                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel('RBX_C_SRTR'))
        
        btn = MTButton('Сортировать')
        btn.clicked.connect(RobloxCookieSorter)
        main_layout.addWidget(btn)