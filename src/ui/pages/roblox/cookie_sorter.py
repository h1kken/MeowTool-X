from __future__ import annotations

import typing as t

from pathlib import Path

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QThread

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTDropZone, MTLabel
from src.services.roblox.cookie_sorter import RobloxCookieSorter

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxCookieSorterPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(
            parent,
            config=config,
            obj_name=obj_name
        )
        
        self._thread: QThread | None = None
        self._sorter: RobloxCookieSorter | None = None

        self._source_files: list[Path] = []
        self._source_file_keys: set[str] = set()
        self._source_text_blocks: list[str] = []
        self._use_default_folder = True

        self._layout = create_layout(LayoutType.VBOX, self)

        self._drop_zone = MTDropZone(
            accept_files=True,
            accept_text=True,
            tr_key='Upload or Drag & Drop text/files here',
            obj_name='Roblox_Cookie_Sorter',
        )
        self._drop_zone.filesDropped.connect(self._add_source_files)
        self._drop_zone.textDropped.connect(self._add_source_text)
        self._layout.addWidget(self._drop_zone)

        self._sort_btn = MTButton(tr_key='CK_SRTR_STRT', obj_name='Roblox_Cookie_Sorter_Start_Button')
        self._sort_btn.clicked.connect(self._start_sorting)

        self._status_label = MTLabel(tr_key='CK_SRTR_STATUS', obj_name='Roblox_Cookie_Sorter_Status')
        self._layout.addWidget(self._status_label)

    def _add_source_files(self, paths: list[Path]) -> None:
        changed = False
        for path in paths:
            key = self._path_key(path)
            if key in self._source_file_keys:
                continue
            self._source_file_keys.add(key)
            self._source_files.append(path)
            changed = True

        if changed:
            self._status_label.setText(f'Added files/folders: +{len(paths)}')

    def _add_source_text(self, text: str) -> None:
        if not text.strip():
            return
        self._source_text_blocks.append(text)
        self._status_label.setText('Added text block')

    def _set_default_folder_mode(self, checked: bool) -> None:
        self._use_default_folder = bool(checked)

    def _clear_sources(self) -> None:
        self._source_files.clear()
        self._source_file_keys.clear()
        self._source_text_blocks.clear()

    def _start_sorting(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return

        if not any((self._use_default_folder, self._source_files, self._source_text_blocks)):
            return

        self._thread = QThread(self)
        self._sorter = RobloxCookieSorter(
            self._config,
            input_paths=list(self._source_files),
            text_chunks=list(self._source_text_blocks),
            use_default_folder=self._use_default_folder,
        )
        self._sorter.moveToThread(self._thread)

        self._thread.started.connect(self._sorter.run)
        self._sorter.finished.connect(self._thread.quit)
        self._sorter.finished.connect(self._on_finished)
        self._thread.finished.connect(self._cleanup_worker)

        self._sort_btn.setEnabled(False)
        self._thread.start()

    def _on_finished(self) -> None:
        self._sort_btn.setEnabled(True)

    def _cleanup_worker(self) -> None:
        self._sort_btn.setEnabled(True)
        if self._sorter is not None:
            self._sorter.deleteLater()
            self._sorter = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def _path_key(self, path: Path) -> str:
        try:
            return str(path.resolve()).lower()
        except OSError:
            return str(path.absolute()).lower()
