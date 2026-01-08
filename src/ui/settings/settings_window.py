from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.ui.widgets.custom_widgets import MTLabel


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(MTLabel('Настройки'))