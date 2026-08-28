from __future__ import annotations

import typing as t

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHeaderView

from src.db.models.cookie_sorter.run import CookieSorterRun
from src.services.base_worker import BaseWorker
from src.translation import TranslationKey as TrKey
from src.services.roblox import RobloxCookieSorter
from src.ui.controllers import PageController
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.models.threads import ThreadsTableModel
from src.ui.pages import BasePage, BasePreparePage
from src.ui.widgets.common import MTButton, MTCounter, MTProgressBar, MTTable, MTScrollArea, MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


class RobloxCookieSorterPage(BasePage):
    _OBJECT_NAME = 'Roblox_Cookie_Sorter'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        parent_page_controller: PageController,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, RobloxCookieSorterPage._OBJECT_NAME))
        self._parent_page_controller = parent_page_controller
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._tabs_widget = MTScrollArea(obj_name=(obj_name, 'Tabs'))
        self._main_layout.addWidget(self._tabs_widget)
        
        self._tabs_container_widget = MTWidget(obj_name=(obj_name, 'Tabs_Container'))
        self._tabs_container_layout = create_layout(LayoutType.HBOX, self._tabs_container_widget)
        self._tabs_widget.setWidget(self._tabs_container_widget)

        self._page_controller = PageController(self._main_layout, parent_page_controller=self._parent_page_controller)

        self._prepare_page = self._create_prepare_page()
        
        self._connect_signals()
        
    def _connect_signals(self) -> None:
        self._prepare_page.startClicked.connect(self._create_run_page)
    
    def _on_run_created(self, run: CookieSorterRun, button: MTButton) -> None:
        button.set_tr(TrKey(key='RUN', suffix=f' #{run.id}'))
        
    def _create_prepare_page(self) -> BasePreparePage:
        obj_name = self.objectName()
        tr = TrKey(key='PREPARE')
        name = 'Prepare'

        page = BasePreparePage(worker_class=RobloxCookieSorter, config=self._config, obj_name=(obj_name,))
        button = MTButton(tr=tr, obj_name=(obj_name, name, 'Tab'))
        self._tabs_container_layout.addWidget(button)
        
        self._page_controller.add_page(key=tr.key, name=name, page=page, button=button)
        return page
        
    def _create_run_page(self, worker: BaseWorker) -> None:
        obj_name = self.objectName()
        tr = TrKey(key='RUN')
        name = 'Run'
        
        page = RobloxCookieSorterRunPage(worker=worker, config=self._config, obj_name=(obj_name,))
        button = MTButton(tr=tr, obj_name=(obj_name, name, 'Tab'))
        self._tabs_container_layout.addWidget(button)
        
        def on_run_created(run: CookieSorterRun) -> None:
            button.set_tr(TrKey(key='RUN', suffix=f' #{run.id}'))
        
        page.runCreated.connect(on_run_created) # lambda should be casted, i wont
        
        self._page_controller.add_page(key=tr.key, name=name, page=page, button=button)
        
    @property
    def page_controller(self) -> PageController | None:
        return self._page_controller


class RobloxCookieSorterRunPage(BasePage):
    runCreated = Signal(object)
    
    _OBJECT_NAME = 'Run'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        worker: BaseWorker,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, RobloxCookieSorterRunPage._OBJECT_NAME))
        self._worker = worker

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        # threads table
        self._threads_model = ThreadsTableModel(self)
        self._threads_table = MTTable(model=self._threads_model, obj_name=(obj_name,))
        self._main_layout.addWidget(self._threads_table)
        
        header = self._threads_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsMovable(False)
        
        self._main_layout.addStretch()
        
        # progress bar
        self._progress_bar = MTProgressBar(obj_name=(obj_name,))
        self._main_layout.addWidget(self._progress_bar)
        
        # counters
        self._counters_widget = MTWidget(obj_name=(obj_name, 'Counters'))
        self._counters_layout = create_layout(LayoutType.HBOX, self._counters_widget)
        self._main_layout.addWidget(self._counters_widget)

        self._valid_counter = MTCounter(tr=TrKey(key='VALID'), obj_name=(obj_name, 'Valid'))
        self._counters_layout.addWidget(self._valid_counter)

        self._duplicate_counter = MTCounter(tr=TrKey(key='DUPLICATE'), obj_name=(obj_name, 'Duplicate'))
        self._counters_layout.addWidget(self._duplicate_counter)

        self._invalid_counter = MTCounter(tr=TrKey(key='INVALID'), obj_name=(obj_name, 'Invalid'))
        self._counters_layout.addWidget(self._invalid_counter)

        self._actions_widget = MTWidget(obj_name=(obj_name, 'Actions'))
        self._actions_layout = create_layout(LayoutType.HBOX, self._actions_widget)
        self._main_layout.addWidget(self._actions_widget)

        # actions
        self._pause_button = MTButton(tr=TrKey(key='PAUSE'), obj_name=(obj_name, 'Pause'), checkable=True)
        self._actions_layout.addWidget(self._pause_button)

        self._stop_button = MTButton(tr=TrKey(key='STOP'), obj_name=(obj_name, 'Stop'))
        self._actions_layout.addWidget(self._stop_button)

    def _connect_signals(self) -> None:
        self._worker.runCreated.connect(self._on_run_created)
        self._worker.progress.connect(self._on_progress_updated)
        self._worker.finished.connect(self._on_run_finished)
        self._pause_button.toggled.connect(self._on_pause_toggled)
        self._stop_button.clicked.connect(self._on_stop_clicked)

    def _on_run_created(self, run: CookieSorterRun) -> None:
        self.runCreated.emit(run)

    def _on_run_finished(self) -> None:
        self._pause_button.setEnabled(False)

    def _on_progress_updated(self, progress: dict[str, int]) -> None:
        self._valid_counter.set_value(progress['valid'])
        self._duplicate_counter.set_value(progress['duplicate'])
        self._invalid_counter.set_value(progress['invalid'])

    def _on_pause_toggled(self, paused: bool) -> None:
        self._worker.pause(paused)
        self._pause_button.set_tr(TrKey(key='UNPAUSE' if paused else 'PAUSE'))
    
    def _on_stop_clicked(self) -> None:
        self._worker.stop()
        self._on_pause_toggled(False)
