from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QResizeEvent

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTSwitch
from src.ui.widgets.settings import MTBaseSetting

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTCheckBoxSetting(MTBaseSetting[bool]):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr_key: str = '',
        obj_name: str = '',
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        self.setObjectName(f'{obj_name}_CheckBox_Setting')

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
        self._main_layout.addWidget(self._label)

        self._main_layout.addStretch()

        self._check_box = MTSwitch(obj_name=f'{obj_name}_CheckBox')
        self._check_box.setChecked(self.value)
        self._main_layout.addWidget(self._check_box)

    def _connect_signals(self) -> None:
        self._check_box.toggled.connect(self._on_check_box_toggled)
        self._config.configLoaded.connect(lambda: self._check_box.setChecked(self.value))

    def _on_check_box_toggled(self, checked: bool) -> None:
        self.value = checked

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._check_box.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )
