from __future__ import annotations

import typing as t

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QWidget, QHeaderView

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTDropZone, MTTable, MTWidget
from src.ui.models.prepare import PrepareTableItem, PrepareTableModel
from src.ui.models.prepare.delegates import PathDelegate, DeleteButtonDelegate
from src.services.roblox.cookie_sorter import RobloxCookieSorter
from src.utils.filesystem import FS

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxCookieSorterPage(BasePage):
    _OBJECT_NAME = 'Roblox_Cookie_Sorter'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, RobloxCookieSorterPage._OBJECT_NAME))
        
        self._thread: QThread | None = None
        self._sorter: RobloxCookieSorter | None = None

        self._dropped_files_keys: set[str] = set()

        self._build_ui()
        self._connect_signals()
        
    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._content_widget = MTWidget(obj_name=(obj_name, 'Content'))
        self._content_layout = create_layout(LayoutType.VBOX, self._content_widget)
        self._main_layout.addWidget(self._content_widget)

        self._drop_zone = MTDropZone(tr_key='UPLD_OR_DRG_AND_DRP_TXT_OR_FLS_HERE', obj_name=(obj_name,))
        self._content_layout.addWidget(self._drop_zone, stretch=1)
        
        self._table = MTTable(obj_name=(obj_name,))
        
        self._model = PrepareTableModel(self)
        self._table.setModel(self._model)
        
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsMovable(False)
        
        self._path_delegate = PathDelegate(self._table)
        self._table.setItemDelegateForColumn(1, self._path_delegate)
        
        self._delete_button_delegate = DeleteButtonDelegate(self._table)
        self._table.setItemDelegateForColumn(3, self._delete_button_delegate)
        
        self._content_layout.addWidget(self._table, stretch=1)
        
        self._buttons_widget = MTWidget(obj_name=(obj_name, 'Buttons'))
        self._buttons_layout = create_layout(LayoutType.HBOX, self._buttons_widget)
        self._main_layout.addWidget(self._buttons_widget)
        
        self._clear_button = MTButton(tr_key='CLR_DT', obj_name=(obj_name, 'Clear'))
        self._clear_button.hide()
        self._buttons_layout.addWidget(self._clear_button)
        
        self._buttons_layout.addStretch()
        
        self._start_button = MTButton(tr_key='CK_SRTR_STRT', obj_name=(obj_name, 'Start'))
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

    def _start(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        if not self._model.items:
            return

        self._thread = QThread(self)
        self._sorter = RobloxCookieSorter(self._config)
        self._sorter.moveToThread(self._thread)

        self._thread.started.connect(self._sorter.run)
        self._sorter.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_worker)

        self._thread.start()

    def _cleanup_worker(self) -> None:
        for obj in (self._sorter, self._thread):
            if obj is not None:
                obj.deleteLater()
                obj = None
