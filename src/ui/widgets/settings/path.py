from __future__ import annotations

import typing as t

from pathlib import Path

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QFileDialog, QWidget

from src.app.paths import PATH_ROOT
from src.translation import TranslationKey as TrKey
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTLabel, MTLineEdit
from src.ui.widgets.settings import MTBaseSetting

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


class MTPathSetting(MTBaseSetting[str]):
    _OBJECT_NAME = 'Path'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...]= (),
        mode: str = 'directory',
        file_filter: str = '',
        caption: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            config=config,
            cfg_key=cfg_key,
            type_=str,
            obj_name=(*obj_name, MTPathSetting._OBJECT_NAME),
        )
        self._mode = mode
        self._file_filter = file_filter
        self._caption = caption.strip() if isinstance(caption, str) and caption.strip() else None

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

        self._line_edit = MTLineEdit(obj_name=(obj_name,))
        self._line_edit.setText(str(self.value).strip())
        self._main_layout.addWidget(self._line_edit, stretch=1)

        self._browse_button = MTButton(obj_name=(obj_name, 'Browse'))
        self._main_layout.addWidget(self._browse_button)
        
    def _connect_signals(self) -> None:
        self._config.configLoaded.connect(self._on_config_loaded)
        self._line_edit.editingFinished.connect(self._on_value_changed)
        self._browse_button.clicked.connect(self._browse_path)

    def _on_config_loaded(self) -> None:
        with QSignalBlocker(self._line_edit):
            self._line_edit.setText(str(self.value).strip())

    def _on_value_changed(self) -> None:
        self.value = self._line_edit.text().strip()

    def _browse_path(self) -> None:
        caption = self._caption or self._label.text().strip() or 'Select path'
        start_path = self._dialog_start_path()

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
        self._on_value_changed()

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
