from PySide6.QtWidgets import QWidget
from src.ui.widgets.custom_widgets import MTLabel, MTButton
# from src.services.roblox import RobloxCookieChecker
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class RobloxCookieCheckerPage(QWidget):
    def __init__(self):
        super().__init__()
                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel('RBX_C_CHCKR'))
        
        btn = MTButton('Чекать')
        # btn.clicked.connect(RobloxCookieRefresher)
        main_layout.addWidget(btn)
