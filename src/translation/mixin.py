from PySide6.QtCore import Qt

from src.translation import translator as t


class TranslatableMixin:
    def __init__(self, key: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._key = key
        t.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        self.setText(t.tr(self._key))
        

class TranslatableComboBoxMixin:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        t.language_changed.connect(self._update_items_text)

    def add_item(self, item: str) -> None:
        self.addItem(t.tr(item), item)
        index = self.count() - 1
        self.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_items_text(self) -> None:
        for i in range(self.count()):
            key = self.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if key is None:
                continue
            self.setItemText(i, t.tr(key))
        sync_content_width = getattr(self, 'sync_content_width', None)
        if callable(sync_content_width):
            sync_content_width()
