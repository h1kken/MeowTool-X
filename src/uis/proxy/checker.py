from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ..custom_widgets import MTLabel, MTButton

class ProxyChecker(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Прокси чекер'))
        layout.addWidget(MTButton('Чекать'))