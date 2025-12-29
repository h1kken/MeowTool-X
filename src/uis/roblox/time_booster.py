from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.uis.widgets.custom_widgets import MTLabel, MTButton


class RobloxTimeBooster(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Бустер времени'))
        layout.addWidget(MTButton('Бустить'))