from src.translation.manager import translator as t


class TranslatableMixin:
    def __init__(self, key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = key
        t.language_changed.connect(self.update_text)
        self.update_text()

    def update_text(self):
        self.setText(t.tr(self.key))