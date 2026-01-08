from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.ui.widgets.custom_widgets import MTLabel, MTButton


class RobloxTimeBoosterWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Бустер времени'))
        layout.addWidget(MTButton('Бустить'))