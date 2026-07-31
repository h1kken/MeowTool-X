from __future__ import annotations

import typing as t

import re

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import  MTLabel, MTComboBox
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config


class MTComboBoxSetting(MTBaseSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        tr_key: str = '',
        items: t.Sequence[str | tuple[str, str]],
        default: str,
        on_changed: t.Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        self._on_changed = on_changed
        self._default = default
        
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_ComboBox_Setting')

        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')
        self._label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        self._combo_box = MTComboBox(obj_name=f'{obj_name}_ComboBox')
        self._combo_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._combo_box.set_content_width_mode('current')
        self.set_items(items, keep_current=False)

        self._set_current_value(config.get(self._cfg_key), fallback=default)
        self._combo_box.currentIndexChanged.connect(self._on_index_changed)
        config.configLoaded.connect(lambda d=default: self._set_current_value(config.get(self._cfg_key), fallback=d))

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._combo_box, 1)

    def set_items(
        self, items: t.Sequence[str | tuple[str, str]], *, keep_current: bool = True
    ) -> None:
        current_value: str | None = None
        if keep_current:
            current_index = self._combo_box.currentIndex()
            current_data = self._combo_box.itemData(current_index)
            current_value = (
                str(current_data)
                if current_data is not None
                else self._combo_box.currentText()
            )

        seen: set[str] = set()
        normalized_items: list[tuple[str, str, bool]] = []
        for item in items:
            if isinstance(item, tuple):
                display_text, value = item
                display_value = str(display_text).strip()
                raw_value = str(value).strip()
                translatable = False
            else:
                raw_value = str(item).strip()
                display_value = raw_value
                translatable = True

            value = raw_value
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_items.append((display_value, value, translatable))

        target_value = current_value if keep_current else str(self._config.get(self._cfg_key))

        with QSignalBlocker(self._combo_box):
            self._combo_box.clear()
            for display_text, value, translatable in normalized_items:
                if translatable:
                    self._combo_box.add_item(value)
                    continue
                self._combo_box.addItem(display_text, value)
            self._set_current_value(target_value, fallback=self._default)

    def _set_current_value(self, value: t.Any, *, fallback: str | None = None) -> None:
        index = self._find_index(value)
        if index < 0 and fallback is not None:
            index = self._find_index(fallback)
        if index < 0 and self._combo_box.count() > 0:
            index = 0
        if index >= 0:
            self._combo_box.setCurrentIndex(index)

    def _find_index(self, value: t.Any) -> int:
        if value is None:
            return -1

        needle = str(value).strip()
        if not needle:
            return -1

        index = self._combo_box.findData(needle)
        if index >= 0:
            return index
        index = self._combo_box.findText(needle)
        if index >= 0:
            return index

        needle_cf = needle.casefold()
        for idx in range(self._combo_box.count()):
            data = self._combo_box.itemData(idx)
            if isinstance(data, str) and data.casefold() == needle_cf:
                return idx
            text = self._combo_box.itemText(idx)
            if text.casefold() == needle_cf:
                return idx

        return -1

    def _on_index_changed(self, index: int) -> None:
        value = self._combo_box.itemData(index)
        if value is None:
            value = self._combo_box.currentText()
        self._config.set(self._cfg_key, value)
        if self._on_changed is not None:
            self._on_changed(str(value))
