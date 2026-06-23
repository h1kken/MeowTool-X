from collections.abc import Callable
from typing import cast

from PySide6.QtCore import Qt

from src.translation.manager import translator as t


class TranslatableMixin:
    def __init__(self, key: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._key = key
        t.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        set_text = getattr(self, 'setText', None)
        if callable(set_text):
            cast_set_text = cast(Callable[[str], None], set_text)
            cast_set_text(t.tr(self._key))
        

class TranslatableComboBoxMixin:
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        t.language_changed.connect(self._update_items_text)

    def add_item(self, item: str) -> None:
        add_item = getattr(self, 'addItem', None)
        count = getattr(self, 'count', None)
        set_item_data = getattr(self, 'setItemData', None)
        if not all(callable(method) for method in (add_item, count, set_item_data)):
            return
        add_item_fn = cast(Callable[[str, object], None], add_item)
        count_fn = cast(Callable[[], int], count)
        set_item_data_fn = cast(Callable[[int, object, int], None], set_item_data)
        add_item_fn(t.tr(item), item)
        index = count_fn() - 1
        set_item_data_fn(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _update_items_text(self) -> None:
        count = getattr(self, 'count', None)
        item_data = getattr(self, 'itemData', None)
        set_item_text = getattr(self, 'setItemText', None)
        if not all(callable(method) for method in (count, item_data, set_item_text)):
            return
        count_fn = cast(Callable[[], int], count)
        item_data_fn = cast(Callable[[int, int], object | None], item_data)
        set_item_text_fn = cast(Callable[[int, str], None], set_item_text)
        for i in range(count_fn()):
            key = item_data_fn(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(key, str):
                continue
            set_item_text_fn(i, t.tr(key))
        sync_content_width = getattr(self, 'sync_content_width', None)
        if callable(sync_content_width):
            sync_content_width()
