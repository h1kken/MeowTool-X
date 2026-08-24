from __future__ import annotations

import typing as t

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTSlider, MTSpinBox
from src.ui.widgets.settings import MTBaseSetting

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTSliderSetting(MTBaseSetting[int]):
    _OBJECT_NAME = 'Slider'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
        min_value: int,
        max_value: int,
    ) -> None:
        super().__init__(
            parent,
            config=config,
            cfg_key=cfg_key,
            type_=int,
            obj_name=(*obj_name, MTSliderSetting._OBJECT_NAME),
        )
        
        self._prev_value = self.value
        self._min_value = min_value
        self._max_value = max_value
        
        self._build_ui(tr=tr)
        self._connect_signals()
        
    def _build_ui(
        self,
        *,
        tr: TrKey,
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._info_layout = create_layout(LayoutType.HBOX)
        self._main_layout.addLayout(self._info_layout)
        
        self._label = MTLabel(tr=tr, obj_name=(obj_name,))
        self._info_layout.addWidget(self._label)

        self._info_layout.addStretch()
        
        self._spin_box = MTSpinBox(obj_name=(obj_name,))
        self._spin_box.setRange(self._min_value, self._max_value)
        self._spin_box.setValue(self._prev_value)
        self._info_layout.addWidget(self._spin_box)

        self._slider = MTSlider(obj_name=(obj_name,))
        self._slider.setRange(self._min_value, self._max_value)
        self._slider.setValue(self._prev_value)
        self._main_layout.addWidget(self._slider)

    def _connect_signals(self) -> None:
        self._config.configLoaded.connect(self._on_config_loaded)
        self._slider.valueChanged.connect(self._spin_box.setValue)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._spin_box.valueChanged.connect(self._slider.setValue)
        self._spin_box.editingFinished.connect(self._on_spin_editing_finished)
        self._spin_box.editingFinished.connect(self._spin_box.clearFocus)

    def _on_config_loaded(self) -> None:
        with QSignalBlocker(self._slider):
            self._slider.setValue(self.value)

    def _set_value_if_changed(self, value: int) -> None:
        if value != self._prev_value:
            self.value = self._prev_value = value

    def _on_slider_released(self) -> None:
        self._set_value_if_changed(self._slider.value())

    def _on_spin_editing_finished(self) -> None:
        self._set_value_if_changed(self._spin_box.value())
