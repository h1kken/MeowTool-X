from src.ui.layouts.enums import LayoutType

# from src.services.roblox import RobloxTimeBooster
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTButton, MTLabel, MTWidget


class RobloxTimeBoosterPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel(tr_key='TM_BSTR', obj_name='Main_Roblox_Time_Booster_Title_Label'))

        btn = MTButton(tr_key='TM_BSTR_STRT', obj_name='Main_Roblox_Time_Booster_Start_Button')
        # btn.clicked.connect(RobloxTimeBooster)
        main_layout.addWidget(btn)
