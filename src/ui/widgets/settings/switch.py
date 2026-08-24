from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTSwitch
from src.ui.widgets.settings import MTBaseSetting

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTSwitchSetting(MTBaseSetting[bool]):
    _OBJECT_NAME = 'Switch'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key, obj_name=(*obj_name, MTSwitchSetting._OBJECT_NAME))
        
        self._build_ui(tr=tr)
        self._connect_signals()

    def _build_ui(
        self,
        *,
        tr: TrKey,
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr=tr, obj_name=(obj_name,))
        self._main_layout.addWidget(self._label)

        self._main_layout.addStretch()
        
        self._switch = MTSwitch(obj_name=(obj_name,))
        self._switch.setChecked(self.value)
        self._main_layout.addWidget(self._switch)
        
    def _connect_signals(self) -> None:
        self._config.configLoaded.connect(self._on_config_loaded)
        self._switch.toggled.connect(self._on_switch_toggled)

    @property
    def label(self) -> MTLabel:
        return self._label

    @property
    def switch(self) -> MTSwitch:
        return self._switch

    def _on_config_loaded(self) -> None:
        with QSignalBlocker(self._switch):
            self._switch.setChecked(self.value)

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
        self._switch.sync_size(bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (child is self._switch or self._switch.isAncestorOf(child)):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self.set_checked(not self.is_checked(), emit_signal=True)
                    event.accept()
                    return

        super().mouseReleaseEvent(event)
