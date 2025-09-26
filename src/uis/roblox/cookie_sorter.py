from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ..custom_widgets import MTLabel, MTButton

class RobloxCookieSorter(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Роблокс куки сортер'))
        layout.addWidget(MTButton('Сортировать'))