from __future__ import annotations

import typing as t

from pathlib import Path
from dataclasses import dataclass

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QWidget, QHeaderView

from src.translation import TranslationKey as TrKey
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTDropZone, MTTable, MTWidget
from src.ui.models.prepare import PrepareTableItem, PrepareTableModel
from src.ui.models.prepare.delegates import PathDelegate, DeleteButtonDelegate
from src.utils.filesystem import FS

if t.TYPE_CHECKING:
    from src.config import Config
    from src.services.base_worker import BaseWorker


@dataclass(frozen=True, slots=True)
class RunSpec:
    run_id: int
    thread: QThread
    worker: BaseWorker


class BasePreparePage(BasePage):
    _OBJECT_NAME = 'Prepare'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        worker_class: type[BaseWorker],
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, BasePreparePage._OBJECT_NAME))
        
        self._thread: QThread | None = None
        
        self._runs: list[RunSpec] = []
        self._worker_class: type[BaseWorker] = worker_class

        self._dropped_files_keys: set[str] = set()

        self._build_ui()
        self._connect_signals()
        
    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._content_widget = MTWidget(obj_name=(obj_name, 'Content'))
        self._content_layout = create_layout(LayoutType.VBOX, self._content_widget)
        self._main_layout.addWidget(self._content_widget)

        self._drop_zone = MTDropZone(tr=TrKey('DRG_AND_DRP'), obj_name=(obj_name,))
        self._content_layout.addWidget(self._drop_zone, stretch=1)
        
        self._data_table = MTTable(obj_name=(obj_name,))
        
        self._model = PrepareTableModel(self)
        self._data_table.setModel(self._model)
        
        header = self._data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsMovable(False)
        
        self._path_delegate = PathDelegate(self._data_table)
        self._data_table.setItemDelegateForColumn(1, self._path_delegate)
        
        self._delete_button_delegate = DeleteButtonDelegate(self._data_table)
        self._data_table.setItemDelegateForColumn(3, self._delete_button_delegate)
        
        self._content_layout.addWidget(self._data_table, stretch=1)
        
        self._buttons_widget = MTWidget(obj_name=(obj_name, 'Buttons'))
        self._buttons_layout = create_layout(LayoutType.HBOX, self._buttons_widget)
        self._main_layout.addWidget(self._buttons_widget)
        
        self._clear_button = MTButton(tr=TrKey(key='CLR'), obj_name=(obj_name, 'Clear'))
        self._clear_button.hide()
        self._buttons_layout.addWidget(self._clear_button)
        
        self._buttons_layout.addStretch()
        
        self._start_button = MTButton(tr=TrKey(key='STRT'), obj_name=(obj_name, 'Start'))
        self._buttons_layout.addWidget(self._start_button)

    def _connect_signals(self) -> None:
        self._drop_zone.pathsDropped.connect(self._add_files)
        self._drop_zone.textDropped.connect(self._add_text)
        
        self._model.itemAdded.connect(self._on_item_added)
        self._model.itemRemoved.connect(self._on_item_removed)
        
        self._delete_button_delegate.clicked.connect(self._model.remove_item)
        
        self._clear_button.clicked.connect(self._clear)
        self._start_button.clicked.connect(self._start)

    def _on_item_added(self, _item: PrepareTableItem) -> None:
        self._clear_button.show()

    def _on_item_removed(self, item: PrepareTableItem) -> None:
        if isinstance(item.value, Path):
            self._dropped_files_keys.discard(FS.path_key(item.value))
        if not self._model.items:
            self._clear_button.hide()

    def _add_files(self, paths: list[Path]) -> None:
        for path in paths:
            key = FS.path_key(path)
            if key in self._dropped_files_keys:
                continue
            
            self._dropped_files_keys.add(key)
            self._model.add_item(PrepareTableItem.create(value=path, lines=0))

    def _add_text(self, text: str) -> None:
        if not text.strip():
            return
        
        self._model.add_item(PrepareTableItem.create(value=text, lines=0))

    def _clear(self) -> None:
        self._model.clear()
        self._dropped_files_keys.clear()
        self._clear_button.hide()

    def _start(self) -> None: # TODO: self._workers, not self._worker
        if not self._model.items:
            return

        thread = QThread(self)
        worker = self._worker_class(self._config)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._cleanup_worker)

        self._runs.append(RunSpec(
            run_id=,
            thread=thread,
            worker=worker,
        ))

        thread.start()

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
