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
    from src.config import Config, ConfigLoader
    from src.ui.widgets.types import ComboItem


class MTComboBoxSetting(MTBaseSetting[str]):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr_key: str = '',
        items: t.Sequence[ComboItem],
        on_changed: t.Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_ComboBox_Setting')

        self._items = items
        self._on_changed = on_changed
        
        self._build_ui(tr_key=tr_key, obj_name=obj_name)
        self._connect_signals()

    def _build_ui(
        self,
        *,
        tr_key: str,
        obj_name: str,
    ) -> None:
        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')
        self._label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self._main_layout.addWidget(self._label)

        self._combo_box = MTComboBox(obj_name=f'{obj_name}_ComboBox')
        self._combo_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._combo_box.set_content_width_mode('longest')
        self.set_items(self._items)
        self._main_layout.addWidget(self._combo_box, stretch=1)

    def _connect_signals(self) -> None:
        self._combo_box.currentIndexChanged.connect(self._on_index_changed)
        self._config.configLoaded.connect(self._on_config_loaded)

    def set_items(self, items: t.Sequence[ComboItem]) -> None:
        with QSignalBlocker(self._combo_box):
            self._combo_box.clear()

            for item in items:
                if item.text is None:
                    self._combo_box.add_item(item.tr_key)
                else:
                    self._combo_box.addItem(item.text, item.tr_key)

        self._set_current_value(self.value)

    def _set_current_value(self, value: str) -> None:
        index = self._combo_box.findData(value)
        if index >= 0:
            self._combo_box.setCurrentIndex(index)

    def _on_config_loaded(self) -> None:
        with QSignalBlocker(self._combo_box):
            self._set_current_value(self.value)

    def _on_index_changed(self, index: int) -> None:
        value = self._combo_box.itemData(index)

        if isinstance(value, str):
            self.value = value
            if self._on_changed:
                self._on_changed(value)
