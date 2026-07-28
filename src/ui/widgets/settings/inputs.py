from __future__ import annotations

import re
from pathlib import Path
import typing as t

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFileDialog, QSizePolicy, QWidget

import src.app.context as ctx
config = ctx.services.config
from src.app.paths import PATH_FOLDER_ICON, PATH_ROOT
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTButton,
    MTDoubleSpinBox,
    MTLabel,
    MTLineEdit,
    MTSlider,
    MTSpinBox,
    MTWidget,
)
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN


class MTTextSetting(MTWidget):
    def __init__(
        self,
        tr_key: str,
        cfg_key: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cfg_key = cfg_key
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Text_Setting")

        self._layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")

        self._line_edit = MTLineEdit(obj_name=f"{obj_name}_LineEdit")
        self._line_edit.setText(str(config.get(self._cfg_key)))
        self._line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._line_edit.editingFinished.connect(self._on_changed)
        config.config_loaded.connect(lambda : self._line_edit.setText(str(config.get(self._cfg_key)).strip()))

        self._layout.addWidget(self._label)
        self._layout.addWidget(self._line_edit, 1)

    def _on_changed(self) -> None:
        config.set(self._cfg_key, self._line_edit.text())


class MTPathSetting(MTWidget):
    def __init__(
        self,
        tr_key: str = '',
        cfg_key: str = '',
        *,
        mode: str = "directory",
        file_filter: str = "",
        caption: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cfg_key = cfg_key
        self._mode = mode
        self._file_filter = file_filter
        self._caption = caption.strip() if isinstance(caption, str) and caption.strip() else None
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Path_Setting")

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")

        self._line_edit = MTLineEdit(obj_name=f"{obj_name}_LineEdit")
        self._line_edit.setText(str(config.get(self._cfg_key)).strip())

        self._browse_button = MTButton(tr_key="", obj_name=f"{obj_name}_Browse_Button")
        self._browse_button.setText("")
        self._browse_button.set_text_icon(
            source=str(PATH_FOLDER_ICON),
            align="center",
            size=QSize(18, 18),
            spacing=0.0,
        )

        self._line_edit.editingFinished.connect(self._on_changed)
        self._browse_button.clicked.connect(self._browse_path)
        config.config_loaded.connect(lambda: self._line_edit.setText(str(config.get(self._cfg_key)).strip()))

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._line_edit, 1)
        self._main_layout.addWidget(self._browse_button)

    def _on_changed(self) -> None:
        config.set(self._cfg_key, self._line_edit.text())

    def _browse_path(self) -> None:
        caption = self._caption or self._label.text().strip() or "Select path"
        start_path = self._dialog_start_path()

        selected_path = ""
        if self._mode == "open-file":
            selected_path, _ = QFileDialog.getOpenFileName(
                self,
                caption,
                start_path,
                self._file_filter,
            )
        elif self._mode == "save-file":
            selected_path, _ = QFileDialog.getSaveFileName(
                self,
                caption,
                start_path,
                self._file_filter,
            )
        else:
            selected_path = QFileDialog.getExistingDirectory(
                self,
                caption,
                start_path,
            )

        if not selected_path:
            return

        self._line_edit.setText(selected_path)
        self._on_changed()

    def _dialog_start_path(self) -> str:
        text = self._line_edit.text().strip()
        if not text:
            return str(PATH_ROOT)

        path = Path(text).expanduser()
        if path.exists():
            if path.is_dir():
                return str(path)
            return str(path.parent)

        parent = path.parent
        if parent.exists():
            return str(parent)
        return str(PATH_ROOT)


class MTSliderSetting(MTWidget):
    def __init__(
        self,
        tr_key: str,
        cfg_key: str,
        min_value: int | float,
        max_value: int | float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._cfg_key = cfg_key
        curr_value = t.cast(int | float, config.get(self._cfg_key))
        if isinstance(curr_value, int):
            min_int = int(min_value)
            max_int = int(max_value)
            self._prev_value = min_int if curr_value <= min_int else max_int if curr_value >= max_int else curr_value
        else:
            min_float = float(min_value)
            max_float = float(max_value)
            self._prev_value = min_float if curr_value <= min_float else max_float if curr_value >= max_float else curr_value

        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Slider_Setting")

        self._main_layout = create_layout(LayoutType.VBOX, parent=self)
        self._info_layout = create_layout(LayoutType.HBOX)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")

        if isinstance(curr_value, int):
            self._spin_box = MTSpinBox(obj_name=f"{obj_name}_SpinBox")
            self._spin_box.setRange(int(min_value), int(max_value))
            self._spin_box.setValue(int(self._prev_value))
        else:
            self._spin_box = MTDoubleSpinBox(obj_name=f"{obj_name}_DoubleSpinBox")
            self._spin_box.setRange(float(min_value), float(max_value))
            self._spin_box.setValue(float(self._prev_value))
            
        self._spin_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # TODO: incorrect for float spinbox
        self._slider = MTSlider(obj_name=f"{obj_name}_Slider")
        self._slider.setRange(int(min_value), int(max_value))
        self._slider.setValue(int(self._prev_value))

        self._slider.valueChanged.connect(self._spin_box.setValue)
        self._spin_box.valueChanged.connect(self._slider.setValue)
        self._spin_box.editingFinished.connect(lambda: self._on_changed(self._spin_box.value()))
        self._spin_box.editingFinished.connect(self._spin_box.clearFocus)
        self._slider.sliderReleased.connect(lambda: self._on_changed(self._slider.value()))
        config.config_loaded.connect(lambda: self._slider.setValue(t.cast(int, config.get(self._cfg_key))))

        self._info_layout.addWidget(self._label)
        self._info_layout.addStretch()
        self._info_layout.addWidget(self._spin_box)
        self._main_layout.addLayout(self._info_layout)
        self._main_layout.addWidget(self._slider)

    def _on_changed(self, value: int | float) -> None:
        if self._spin_box.value() != self._prev_value:
            self._prev_value = self._spin_box.value()
            config.set(self._cfg_key, value)

    @property
    def spin_box(self) -> MTSpinBox | MTDoubleSpinBox:
        return self._spin_box

    @property
    def slider(self) -> MTSlider:
        return self._slider
