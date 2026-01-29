from src.translation import translator as t


class TranslatableMixin:
    def __init__(self, key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key = key
        t.language_changed.connect(self.update_text)
        self.update_text()

    def update_text(self):
        self.setText(t.tr(self._key))