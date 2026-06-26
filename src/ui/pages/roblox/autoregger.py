from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTLabel, MTWidget


class RobloxAutoReggerPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel(tr_key='AT_RGGR', obj_name='Main_Roblox_Auto_Regger_Title_Label'))
