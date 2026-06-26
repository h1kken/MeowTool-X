from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTButton, MTLabel, MTWidget


class RobloxCookieCheckerPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel(tr_key='CK_CHCKR', obj_name='Main_Roblox_Cookie_Checker_Title_Label'))

        btn = MTButton(tr_key='CK_CHCKR_STRT', obj_name='Main_Roblox_Cookie_Checker_Start_Button')
        main_layout.addWidget(btn)