from __future__ import annotations

import typing as t

import re

from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTLabel, MTLineEdit
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config


class MTLineEditSetting(MTBaseSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        tr_key: str = '',
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_Text_Setting')

        self._layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')

        self._line_edit = MTLineEdit(obj_name=f'{obj_name}_LineEdit')
        self._line_edit.setText(str(config.get(self._cfg_key)))
        self._line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._line_edit.editingFinished.connect(self._on_changed)
        config.configLoaded.connect(lambda : self._line_edit.setText(str(config.get(self._cfg_key)).strip()))

        self._layout.addWidget(self._label)
        self._layout.addWidget(self._line_edit, 1)

    def _on_changed(self) -> None:
        self._config.set(self._cfg_key, self._line_edit.text())
