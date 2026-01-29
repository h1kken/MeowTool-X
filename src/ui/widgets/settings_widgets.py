import re
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTLabel, MTButton, MTCheckBox,
    MTSlider, MTWidget, MTDoubleSpinBox,
    MTSpinBox,
)
from src.utils.regex import NORMALIZE_QT_KEY_PATTERN
from src.utils.pyside6 import connect


class ColumnsSetting(QWidget):
    def __init__(
        self,
        tabs: Optional[list[QWidget]] = None,
        columns: int = 2,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._columns = columns
        self._layouts: list[QVBoxLayout] = []
        
        self._main_layout = create_layout(LayoutType.HBOX, parent=self)
        
        for _ in range(columns):
            column_layout = create_layout(LayoutType.VBOX)
            self._main_layout.addLayout(column_layout, stretch=2)
            self._layouts.append(column_layout)

        if tabs:
            for i, tab in enumerate(tabs):
                self._layouts[i % columns].addWidget(tab)

            for l in self._layouts:
                l.addStretch()


class CollapsibleContainer(QWidget):
    def __init__(
        self,
        tr_key: str,
        obj_name: str,
        widgets: list[QWidget] = [],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        self._main_layout = create_layout(LayoutType.VBOX, parent=self)
        self.setLayout(self._main_layout)
        
        self._header_widget = MTWidget(obj_name=f'{obj_name}_Header_Widget')
        self._header_layout = create_layout(LayoutType.HBOX, parent=self._header_widget)
        
        self._label = MTLabel(tr_key, obj_name=f'{obj_name}_Label')
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._toggle_button = MTButton('▼', checkable=True, checked=True, obj_name=f'{obj_name}_Toggle_Button')
        connect(self._toggle_button.toggled, func=self.toggle_collapsed)

        self._content_widget = MTWidget(obj_name=f'{obj_name}_Content_Widget')
        self._content_layout = create_layout(LayoutType.VBOX, parent=self._content_widget)
        
        self._header_layout.addWidget(self._label)
        self._header_layout.addWidget(self._toggle_button)
        self._main_layout.addWidget(self._header_widget)
        self._main_layout.addWidget(self._content_widget)

        for widget in widgets:
            self._content_layout.addWidget(widget)

    def toggle_collapsed(self, checked: bool) -> None:
        self._content_widget.setVisible(checked)
        self._toggle_button.setText('▼' if checked else '▶')


class CheckboxSetting(QWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: bool,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(30)
        
        self._config = config
        self._cfg_key = cfg_key
                
        name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{name}_Setting')
        
        self._main_layout = create_layout(LayoutType.HBOX, parent=self)
        self.setLayout(self._main_layout)
        
        self._label = MTLabel(tr_key, obj_name=f'{name}_Label')
        
        self._checkbox = MTCheckBox(obj_name=f'{name}_Checkbox')
        self._checkbox.setChecked(self._config.get(self._cfg_key, default=default))
                
        connect(self._checkbox.toggled, func=lambda v: self._config.set(self._cfg_key, v))
        connect(self._config.config_loaded, func=lambda: self._checkbox.setChecked(self._config.get(self._cfg_key)))

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._checkbox)


class SliderSetting(QWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        min_value: int | float,
        max_value: int | float,
        default: int | float,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(30)
        
        self._config = config
        self._cfg_key = cfg_key
        
        value = self._config.get(self._cfg_key, default=default)
        self._prev_value = value if min_value <= value <= max_value else default
        
        name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{name}_Setting')
        
        self._main_layout = create_layout(LayoutType.VBOX, parent=self)
        self.setLayout(self._main_layout)
        self._info_layout = create_layout(LayoutType.HBOX)
        
        self._label = MTLabel(tr_key, obj_name=f'{name}_Label')
        
        if isinstance(default, int):
            self._spin_box = MTSpinBox(obj_name=f'{name}_SpinBox')
        else:
            self._spin_box = MTDoubleSpinBox(obj_name=f'{name}_DoubleSpinBox')
            
        self._spin_box.setRange(min_value, max_value)
        self._spin_box.setValue(self._prev_value)
        
        self._slider = MTSlider(obj_name=f'{name}_Slider')
        self._slider.setRange(min_value, max_value)
        self._slider.setValue(self._prev_value)
                
        connect(self._slider.valueChanged, func=self._spin_box.setValue)
        connect(self._spin_box.valueChanged, func=self._slider.setValue)
        connect(self._spin_box.editingFinished, func=lambda: self._on_changed(self._spin_box.value()))
        connect(self._spin_box.editingFinished, func=self._spin_box.clearFocus)
        connect(self._slider.sliderReleased, func=lambda: self._on_changed(self._slider.value()))
        connect(self._config.config_loaded, func=lambda d=default: self._slider.setValue(self._config.get(self._cfg_key, default=d)))
        
        self._info_layout.addWidget(self._label)
        self._info_layout.addStretch()
        self._info_layout.addWidget(self._spin_box)
        self._main_layout.addLayout(self._info_layout)
        self._main_layout.addWidget(self._slider)
        
    def _on_changed(self, value: int | float) -> None:
        if self._spin_box.value() != self._prev_value:
            self._prev_value = self._spin_box.value()
            self._config.set(self._cfg_key, value)
