from PySide6.QtWidgets import QWidget
from src.ui.widgets.custom_widgets import MTLabel, MTButton
# from src.services.proxy import ProxyChecker
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class ProxyCheckerPage(QWidget):
    def __init__(self):
        super().__init__()
                                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_layout.addWidget(MTLabel('PRX_CHCKR'))
        
        btn = MTButton('Чекать')
        # btn.clicked.connect(ProxyChecker)
        main_layout.addWidget(btn)
        