from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ..custom_widgets import MTLabel, MTButton

class RobloxCookieChecker(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Роблокс куки чекер'))
        layout.addWidget(MTButton('Чекать'))