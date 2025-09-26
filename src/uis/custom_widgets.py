from PyQt6.QtWidgets import QLabel, QPushButton
from ..translation.mixin import TranslatableMixin


class MTLabel(TranslatableMixin, QLabel):
    def __init__(self, key: str, parent=None):
        super().__init__(key, parent)
        
        
class MTButton(TranslatableMixin, QPushButton):
    def __init__(self, key: str, parent=None):
        super().__init__(key, parent)