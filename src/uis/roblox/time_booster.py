from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ..custom_widgets import MTLabel, MTButton

class RobloxTimeBooster(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Бустер времени'))
        layout.addWidget(MTButton('Бустить'))