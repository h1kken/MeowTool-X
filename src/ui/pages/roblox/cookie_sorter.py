from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.services.roblox import RobloxCookieSorter
from src.ui.controllers import PageController
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.pages import BasePage, BasePreparePage
from src.ui.widgets.common import MTButton, MTCounter, MTProgressBar, MTScrollArea, MTWidget

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

        self._tab_names_by_key: dict[str, str] = {}
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._tabs_widget = MTScrollArea(obj_name=(obj_name, 'Tabs')) # fuck scrollarea's size hint
        self._main_layout.addWidget(self._tabs_widget)
        
        self._tabs_container_widget = MTWidget(obj_name=(obj_name, 'Tabs_Container'))
        self._tabs_container_layout = create_layout(LayoutType.HBOX, self._tabs_container_widget)
        self._tabs_widget.setWidget(self._tabs_container_widget)

        self._page_controller = PageController(self._main_layout, parent_page_controller=self._parent_page_controller)

        tr_key, name = 'PREPARE', 'Prepare'
        self._tab_names_by_key[tr_key] = name

        page = BasePreparePage(worker_class=RobloxCookieSorter, config=self._config, obj_name=(obj_name,))
        button = MTButton(tr_key=tr_key, obj_name=(obj_name, name, 'Tab'))
        self._tabs_container_layout.addWidget(button)
        self._page_controller.add_page(key=tr_key, name=name, page=page, button=button)
        
    @property
    def page_controller(self) -> PageController | None:
        return self._page_controller

    def create_run(self) -> None:
        ...


class RobloxCookieSorterProcessPage(BasePage):
    _OBJECT_NAME = 'Roblox_Cookie_Sorter_Process'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, RobloxCookieSorterProcessPage._OBJECT_NAME))

        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._progress_bar = MTProgressBar(obj_name=(obj_name,))
        self._main_layout.addWidget(self._progress_bar)
        
        self._counters_widget = MTWidget(obj_name=(obj_name, 'Counters'))
        self._counters_layout = create_layout(LayoutType.HBOX, self._counters_widget)
        self._main_layout.addWidget(self._counters_widget)

        self._valid_counter = MTCounter(tr_key='VALID', obj_name=(obj_name, 'Valid'))
        self._counters_layout.addWidget(self._valid_counter)

        self._duplicate_counter = MTCounter(tr_key='DUPLICATE', obj_name=(obj_name, 'Duplicate'))
        self._counters_layout.addWidget(self._duplicate_counter)

        self._invalid_counter = MTCounter(tr_key='INVALID', obj_name=(obj_name, 'Invalid'))
        self._counters_layout.addWidget(self._invalid_counter)
