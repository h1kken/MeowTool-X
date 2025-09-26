from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ..custom_widgets import MTLabel, MTButton

class RobloxCookieRefresher(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Роблокс куки рефрешер'))
        layout.addWidget(MTButton('Рефрешить'))