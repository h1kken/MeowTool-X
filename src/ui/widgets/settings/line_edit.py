from __future__ import annotations

import typing as t

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTLineEdit
from src.ui.widgets.settings import MTBaseSetting

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTLineEditSetting(MTBaseSetting[str]):
    _OBJECT_NAME = 'LineEdit'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key, obj_name=obj_name)

        self._build_ui(tr_key=tr_key)
        self._connect_signals()

    def _build_ui(
        self,
        *,
        tr_key: str = '',
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=(obj_name,))
        self._main_layout.addWidget(self._label)

        self._line_edit = MTLineEdit(obj_name=(obj_name,))
        self._line_edit.setText(self.value)
        self._main_layout.addWidget(self._line_edit, stretch=1)

    def _connect_signals(self) -> None:
        self._config.configLoaded.connect(self._on_config_loaded)
        self._line_edit.editingFinished.connect(self._on_value_changed)

    def _on_config_loaded(self) -> None:
        with QSignalBlocker(self._line_edit):
            self._line_edit.setText(self.value.strip())

    def _on_value_changed(self) -> None:
        self.value = self._line_edit.text().strip()
