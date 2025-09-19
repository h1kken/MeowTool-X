from PyQt6.QtWidgets import QLabel, QPushButton
from translate.translation_manager import translator as t


class TranslatableMixin:
    def __init__(self, key: str):
        self.key = key
        t.language_changed.connect(self.update_text)
        self.update_text()

    def update_text(self):
        if hasattr(self, "setText"):
            self.setText(t.tr(self.key))
        elif hasattr(self, "setWindowTitle"):
            self.setWindowTitle(t.tr(self.key))


class MTLabel(QLabel, TranslatableMixin):
    def __init__(self, key: str, parent=None):
        QLabel.__init__(self, parent)
        TranslatableMixin.__init__(self, key)


class MTButton(QPushButton, TranslatableMixin):
    def __init__(self, key: str, parent=None):
        QPushButton.__init__(self, parent)
        TranslatableMixin.__init__(self, key)
