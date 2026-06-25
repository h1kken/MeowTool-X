import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget

from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTLabel,
    MTWidget,
)
from src.ui.widgets import MTSwitch
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

SETTING_ROW_HEIGHT = 0
SETTING_ROW_GAP = 0
SLIDER_COMPACT_PART_HEIGHT = 0
COLLAPSIBLE_TOGGLE_BUTTON_SIZE = 20
COLLAPSIBLE_TOGGLE_ICON_SIZE = 18


class MTCheckBoxSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_CheckBox_Setting")
        self.setProperty("rainbowBorderTarget", False)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._check_box = MTSwitch(obj_name=f"{obj_name}_CheckBox")
        self._check_box.setChecked(
            bool(self._config.get(self._cfg_key, default=default))
        )

        self._check_box.toggled.connect(self._on_check_box_toggled)
        self._config.config_loaded.connect(
            lambda d=default: self._check_box.setChecked(
                bool(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._check_box)

    def _on_check_box_toggled(self, checked: bool) -> None:
        self._config.set(self._cfg_key, checked)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._check_box.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )


class MTSwitchSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: bool,
        obj_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        obj_name = obj_name or re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Switch_Setting")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._switch = MTSwitch(obj_name=f"{obj_name}_Switch")
        self._switch.setChecked(bool(self._config.get(self._cfg_key, default=default)))
        self._suspend_config_write = False

        self._switch.toggled.connect(self._on_switch_toggled)
        self._config.config_loaded.connect(
            lambda d=default: self._switch.setChecked(
                bool(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._switch)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )

    def _on_switch_toggled(self, value: bool) -> None:
        if self._suspend_config_write:
            return
        self._config.set(self._cfg_key, value)

    def set_checked(self, checked: bool, *, emit_signal: bool = True) -> None:
        target = bool(checked)
        if self._switch.isChecked() == target:
            return
        if emit_signal:
            self._switch.setChecked(target)
            return

        self._suspend_config_write = True
        try:
            self._switch.setChecked(target)
        finally:
            self._suspend_config_write = False

    def is_checked(self) -> bool:
        return self._switch.isChecked()

    @property
    def label(self) -> MTLabel:
        return self._label

    @property
    def switch(self) -> MTSwitch:
        return self._switch

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (
                    child is self._switch or self._switch.isAncestorOf(child)
                ):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self.set_checked(not self.is_checked(), emit_signal=True)
                    event.accept()
                    return

        super().mouseReleaseEvent(event)


class MTSwitchRowSetting(MTWidget):
    def __init__(
        self,
        tr_key: str,
        switch: MTSwitch,
        *,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._switch = switch
        self.setObjectName(f"{obj_name}_Switch_Row_Setting")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(
            tr_key=tr_key,
            obj_name=f"{obj_name}_Label",
        )
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._switch)

    @property
    def label(self) -> MTLabel:
        return self._label

    @property
    def switch(self) -> MTSwitch:
        return self._switch

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (
                    child is self._switch or self._switch.isAncestorOf(child)
                ):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self._switch.setChecked(not self._switch.isChecked())
                    event.accept()
                    return

        super().mouseReleaseEvent(event)
