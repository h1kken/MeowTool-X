from PySide6.QtWidgets import QWidget
from src.ui.widgets.custom_widgets import MTLabel
from src.ui.layouts.factory import create_layout
from src.ui.layouts.enums import LayoutType


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
                
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        
        lbl = MTLabel('ABT', obj_name='About_Label')
        main_layout.addWidget(lbl)
