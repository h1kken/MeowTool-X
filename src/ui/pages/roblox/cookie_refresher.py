from PySide6.QtWidgets import QWidget
from src.ui.widgets.custom_widgets import MTLabel, MTButton
# from src.services.roblox import RobloxCookieRefresher
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class RobloxCookieRefresherPage(QWidget):
    def __init__(self):
        super().__init__()
                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        
        lbl = MTLabel('RBX_C_RFRSHR', obj_name='Roblox_Cookie_Refresher_Label')
        main_layout.addWidget(lbl)
        
        btn = MTButton('Рефрешить', obj_name='Roblox_Cookie_Refresher_Button')
        # btn.clicked.connect(RobloxCookieRefresher)
        main_layout.addWidget(btn)