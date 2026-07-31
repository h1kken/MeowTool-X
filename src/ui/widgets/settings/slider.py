from __future__ import annotations

import typing as t

import re

from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTDoubleSpinBox, MTLabel, MTSlider, MTSpinBox
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config


class MTSliderSetting(MTBaseSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        tr_key: str = '',
        min_value: int | float,
        max_value: int | float,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        
        curr_value = t.cast(int | float, config.get(self._cfg_key))
        if isinstance(curr_value, int):
            min_int = int(min_value)
            max_int = int(max_value)
            self._prev_value = min_int if curr_value <= min_int else max_int if curr_value >= max_int else curr_value
        else:
            min_float = float(min_value)
            max_float = float(max_value)
            self._prev_value = min_float if curr_value <= min_float else max_float if curr_value >= max_float else curr_value

        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_Slider_Setting')

        self._main_layout = create_layout(LayoutType.VBOX, self)
        self._info_layout = create_layout(LayoutType.HBOX)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')

        if isinstance(curr_value, int):
            self._spin_box = MTSpinBox(obj_name=f'{obj_name}_SpinBox')
            self._spin_box.setRange(int(min_value), int(max_value))
            self._spin_box.setValue(int(self._prev_value))
        else:
            self._spin_box = MTDoubleSpinBox(obj_name=f'{obj_name}_DoubleSpinBox')
            self._spin_box.setRange(float(min_value), float(max_value))
            self._spin_box.setValue(float(self._prev_value))
            
        self._spin_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # TODO: incorrect for float spinbox
        self._slider = MTSlider(obj_name=f'{obj_name}_Slider')
        self._slider.setRange(int(min_value), int(max_value))
        self._slider.setValue(int(self._prev_value))

        self._slider.valueChanged.connect(self._spin_box.setValue)
        self._spin_box.valueChanged.connect(self._slider.setValue)
        self._spin_box.editingFinished.connect(lambda: self._on_changed(self._spin_box.value()))
        self._spin_box.editingFinished.connect(self._spin_box.clearFocus)
        self._slider.sliderReleased.connect(lambda: self._on_changed(self._slider.value()))
        config.configLoaded.connect(lambda: self._slider.setValue(t.cast(int, config.get(self._cfg_key))))

        self._info_layout.addWidget(self._label)
        self._info_layout.addStretch()
        self._info_layout.addWidget(self._spin_box)
        self._main_layout.addLayout(self._info_layout)
        self._main_layout.addWidget(self._slider)

    def _on_changed(self, value: int | float) -> None:
        if self._spin_box.value() != self._prev_value:
            self._prev_value = self._spin_box.value()
            self._config.set(self._cfg_key, value)

    @property
    def spin_box(self) -> MTSpinBox | MTDoubleSpinBox:
        return self._spin_box

    @property
    def slider(self) -> MTSlider:
        return self._slider
