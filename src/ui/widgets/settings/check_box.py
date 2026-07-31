from __future__ import annotations

import typing as t

import re

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QResizeEvent

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTSwitch
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config


class MTCheckBoxSetting(MTBaseSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        tr_key: str = '',
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)

        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_CheckBox_Setting')

        self._layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')

        self._check_box = MTSwitch(obj_name=f'{obj_name}_CheckBox')
        self._check_box.setChecked(bool(config.get(self._cfg_key)))

        self._check_box.toggled.connect(self._on_check_box_toggled)
        config.configLoaded.connect(lambda: self._check_box.setChecked(bool(config.get(self._cfg_key))))

        self._layout.addWidget(self._label)
        self._layout.addStretch()
        self._layout.addWidget(self._check_box)

    def _on_check_box_toggled(self, checked: bool) -> None:
        self._config.set(self._cfg_key, checked)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._check_box.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )
