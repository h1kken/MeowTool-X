from __future__ import annotations

import typing as t

import re
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFileDialog, QWidget

from src.app.paths import PATH_FOLDER_ICON, PATH_ROOT
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTLabel, MTLineEdit
from src.ui.widgets.settings import MTBaseSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

if t.TYPE_CHECKING:
    from src.config import Config


class MTPathSetting(MTBaseSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        tr_key: str = '',
        mode: str = 'directory',
        file_filter: str = '',
        caption: str | None = None,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key)
        self._mode = mode
        self._file_filter = file_filter
        self._caption = caption.strip() if isinstance(caption, str) and caption.strip() else None
        
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, '_', self._cfg_key)
        self.setObjectName(f'{obj_name}_Path_Setting')

        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')

        self._line_edit = MTLineEdit(obj_name=f'{obj_name}_LineEdit')
        self._line_edit.setText(str(self._config.get(self._cfg_key)).strip())

        self._browse_button = MTButton(obj_name=f'{obj_name}_Browse_Button')
        self._browse_button.set_icon(
            source=str(PATH_FOLDER_ICON),
            align='center',
            size=QSize(18, 18),
            spacing=0.0,
        )

        self._line_edit.editingFinished.connect(self._on_changed)
        self._browse_button.clicked.connect(self._browse_path)
        self._config.configLoaded.connect(lambda: self._line_edit.setText(str(self._config.get(self._cfg_key)).strip()))

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._line_edit, 1)
        self._main_layout.addWidget(self._browse_button)

    def _on_changed(self) -> None:
        self._config.set(self._cfg_key, self._line_edit.text())

    def _browse_path(self) -> None:
        caption = self._caption or self._label.text().strip() or 'Select path'
        start_path = self._dialog_start_path()

        selected_path = ''
        if self._mode == 'open-file':
            selected_path, _ = QFileDialog.getOpenFileName(
                self,
                caption,
                start_path,
                self._file_filter,
            )
        elif self._mode == 'save-file':
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
