from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.ui.widgets.custom_widgets import MTLabel, MTButton
from src.services.roblox.sorter import RobloxCookieSorter


class RobloxCookieSorterWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Роблокс куки сортер'))
        btn = MTButton('Сортировать')
        btn.clicked.connect(RobloxCookieSorter)
        layout.addWidget(btn)