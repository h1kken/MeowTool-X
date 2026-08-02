from __future__ import annotations

import typing as t

import re

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTWidget, MTLabel, MTSwitch
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTSwitchSetting(MTBaseSetting[bool]):
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
        
        obj_name = obj_name or re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_Switch_Setting')

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
        
        self._switch = MTSwitch(obj_name=f'{obj_name}_Switch')
        self._switch.setChecked(self.value)
        self._main_layout.addWidget(self._switch)
        
    def _connect_signals(self) -> None:
        self._switch.toggled.connect(self._on_switch_toggled)
        self._config.configLoaded.connect(lambda: self._switch.setChecked(self.value))

    def _on_switch_toggled(self, value: bool) -> None:
        self.value = value

    def set_checked(self, checked: bool, *, emit_signal: bool = True) -> None:
        if self._switch.isChecked() == checked:
            return
        if emit_signal:
            self._switch.setChecked(checked)
            return

        with QSignalBlocker(self._switch):
            self._switch.setChecked(checked)

    def is_checked(self) -> bool:
        return self._switch.isChecked()

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
                    self.set_checked(not self.is_checked(), emit_signal=True)
                    event.accept()
                    return

        super().mouseReleaseEvent(event)


class MTSwitchRowSetting(MTWidget): # MTBaseSetting?
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: str = '',
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f'{obj_name}_Switch_Row_Setting')

        self._build_ui(tr_key=tr_key, obj_name=obj_name)

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
        
        self._switch = MTSwitch(obj_name=f'{obj_name}_Switch')
        self._main_layout.addWidget(self._switch)
    
    @property
    def switch(self): return self._switch

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(bounds_width=max(1, self.width() // 3), bounds_height=available_height - 2)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (child is self._switch or self._switch.isAncestorOf(child)):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self._switch.setChecked(not self._switch.isChecked())
                    event.accept()
                    return

        super().mouseReleaseEvent(event)
