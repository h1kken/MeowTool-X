from PySide6.QtWidgets import QWidget
from src.ui.widgets.custom_widgets import MTLabel, MTButton
# from src.services.roblox import RobloxTimeBooster
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class RobloxTimeBoosterPage(QWidget):
    def __init__(self):
        super().__init__()
                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel('RBX_TM_BSTR'))
        
        btn = MTButton('Бустить')
        # btn.clicked.connect(RobloxTimeBooster)
        main_layout.addWidget(btn)