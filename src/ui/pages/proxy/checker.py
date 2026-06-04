from src.ui.layouts.enums import LayoutType

# from src.services.proxy import ProxyChecker
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTButton, MTLabel, MTWidget


class ProxyCheckerPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel(tr_key='PRX_CHCKR', obj_name='Main_Proxy_Checker_Title_Label'))

        btn = MTButton(tr_key='Чекать', obj_name='Main_Proxy_Checker_Start_Button')
        # btn.clicked.connect(ProxyChecker)
        main_layout.addWidget(btn)
