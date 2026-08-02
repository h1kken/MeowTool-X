from __future__ import annotations

import typing as t

import re

from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTSlider, MTSpinBox
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTSliderSetting(MTBaseSetting[int]):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr_key: str = '',
        min_value: int,
        max_value: int,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        
        self._prev_value = self.value
        self._min_value = min_value
        self._max_value = max_value
        
        self._build_ui(tr_key=tr_key)
        self._connect_signals()
        
    def _build_ui(
        self,
        *,
        tr_key: str,
    ) -> None:
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_Slider_Setting')

        self._main_layout = create_layout(LayoutType.VBOX, self)
        self._info_layout = create_layout(LayoutType.HBOX)
        self._main_layout.addLayout(self._info_layout)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')
        self._info_layout.addWidget(self._label)

        self._info_layout.addStretch()
        
        self._spin_box = MTSpinBox(obj_name=f'{obj_name}_SpinBox')
        self._spin_box.setRange(self._min_value, self._max_value)
        self._spin_box.setValue(self._prev_value)
            
        self._spin_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self._info_layout.addWidget(self._spin_box)

        self._slider = MTSlider(obj_name=f'{obj_name}_Slider')
        self._slider.setRange(self._min_value, self._max_value)
        self._slider.setValue(self._prev_value)
        self._main_layout.addWidget(self._slider)

    def _connect_signals(self) -> None:
        self._slider.valueChanged.connect(self._spin_box.setValue)
        self._slider.sliderReleased.connect(lambda: self._on_changed(self._slider.value()))
        self._spin_box.valueChanged.connect(self._slider.setValue)
        self._spin_box.editingFinished.connect(lambda: self._on_changed(self._spin_box.value()))
        self._spin_box.editingFinished.connect(self._spin_box.clearFocus)
        self._config.configLoaded.connect(lambda: self._slider.setValue(self.value))

    def _on_changed(self, value: int) -> None:
        if value != self._prev_value:
            self.value = self._prev_value = value
