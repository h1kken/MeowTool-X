from src.ui.layouts.enums import LayoutType

# from src.services.roblox import RobloxCookieRefresher
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTButton, MTLabel, MTWidget


class RobloxCookieRefresherPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        lbl = MTLabel(tr_key='CK_RFRSHR', obj_name='Main_Roblox_Cookie_Refresher_Title_Label')
        main_layout.addWidget(lbl)

        btn = MTButton(tr_key='CK_RFRSHR_STRT', obj_name='Main_Roblox_Cookie_Refresher_Start_Button')
        # btn.clicked.connect(RobloxCookieRefresher)
        main_layout.addWidget(btn)
