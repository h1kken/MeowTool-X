from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.ui.widgets.custom_widgets import MTLabel, MTButton


class RobloxCookieRefresherWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Роблокс куки рефрешер'))
        layout.addWidget(MTButton('Рефрешить'))