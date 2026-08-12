from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow

from src.app.constants import PROGRAM_TITLE
from src.ui.constants import WINDOW_X, WINDOW_Y
from src.ui.widgets.common.overlay import MTPopupOverlay
from src.ui.windows.types import PageSpec
from src.ui.controllers import PageController
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.pages import (
    ProxyCheckerPage,
    RobloxCookieCheckerPage,
    RobloxCookieRefresherPage,
    RobloxCookieSorterPage,
    SettingsPage,
)
from src.ui.widgets.common import MTButton, MTWidget, MTImage
from src.ui.windows.window_header import MTWindowHeader

if t.TYPE_CHECKING:
    from src.config import Config


_PAGES: tuple[PageSpec | None, ...] = (
    PageSpec(ProxyCheckerPage,          'CHCKR',     'Proxy_Checker',           'checker.svg'),
    PageSpec(RobloxCookieSorterPage,    'CK_SRTR',   'Roblox_Cookie_Sorter',    'sorter.svg'),
    PageSpec(RobloxCookieCheckerPage,   'CK_CHCKR',  'Roblox_Cookie_Checker',   'checker.svg'),
    PageSpec(RobloxCookieRefresherPage, 'CK_RFRSHR', 'Roblox_Cookie_Refresher', 'refresher.svg'),
    None,
    PageSpec(SettingsPage,              'STNGS',     'Settings',                'settings.svg', has_page_controller=True),
)


class MainWindow(QMainWindow):
    pageChanged = Signal(tuple[str, ...])
    
    _OBJECT_NAME = 'Main_Window'
    
    def __init__(
        self,
        config: Config
    ) -> None:
        super().__init__()
        self._config = config
        
        self._tab_names_by_key: dict[str, str] = {}
        
        self._build_ui()
        
        self.pageChanged.connect(lambda: print(self.page_state()))
        
        self._connect_signals()

    def _build_ui(self) -> None:
        self.setObjectName('Main_Window')
        self.setWindowTitle(PROGRAM_TITLE)
        self.resize(WINDOW_X, WINDOW_Y)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self._main_widget = MTWidget(obj_name=(MainWindow._OBJECT_NAME, 'Central_Widget'))
        self._main_layout = create_layout(LayoutType.VBOX, self._main_widget)
        self.setCentralWidget(self._main_widget)
        
        # header
        self._window_header_widget = MTWindowHeader(self)
        self._main_layout.addWidget(self._window_header_widget)
        
        # overlay
        self._body_container_widget = MTWidget(obj_name=(MainWindow._OBJECT_NAME, 'Body_Container'))
        self._body_container_layout = create_layout(LayoutType.GRID, self._body_container_widget)
        self._main_layout.addWidget(self._body_container_widget, stretch=1)

        self._body_content_widget = MTWidget(obj_name=(MainWindow._OBJECT_NAME, 'Body_Content'))
        self._body_content_layout = create_layout(LayoutType.HBOX, self._body_content_widget)
        self._body_container_layout.addWidget(self._body_content_widget, 0, 0)
        
        self._overlay_widget = MTPopupOverlay()
        self._body_container_layout.addWidget(self._overlay_widget, 0, 0)
        
        # sidebar
        self._sidebar_widget = MTWidget(obj_name=(MainWindow._OBJECT_NAME, 'Sidebar'))
        self._sidebar_layout = create_layout(LayoutType.VBOX, self._sidebar_widget)
        self._body_content_layout.addWidget(self._sidebar_widget)
        
        self._sidebar_image_widget = MTImage(self._sidebar_widget, obj_name=(MainWindow._OBJECT_NAME,))
        self._sidebar_layout.addWidget(self._sidebar_image_widget)
        
        # pages
        self._pages_widget = MTWidget(obj_name=(MainWindow._OBJECT_NAME, 'Pages'))
        self._pages_layout = create_layout(LayoutType.VBOX, self._pages_widget)
        self._body_content_layout.addWidget(self._pages_widget, stretch=1)

        self._page_controller = PageController(self._pages_layout)

        for spec in _PAGES:
            if spec is None:
                self._sidebar_layout.addStretch()
                continue
            
            name = str(spec.obj_name).replace('_', ' ')
            self._tab_names_by_key[spec.tr_key] = name
            
            if spec.has_page_controller:
                page = spec.page_class(
                    config=self._config,
                    parent_page_controller=self._page_controller, # type: ignore[call-arg]
                )
            else:
                page = spec.page_class(
                    config=self._config,
                )
                
            button = MTButton(tr_key=spec.tr_key, obj_name=('Sidebar', spec.obj_name, 'Tab'))
            self._sidebar_layout.addWidget(button)
            
            self._page_controller.add_page(
                key=spec.tr_key,
                name=name,
                page=page,
                button=button,
            )
            
    def _connect_signals(self) -> None:
        self._page_controller.pageChanged.connect(self.pageChanged.emit)

    @property
    def overlay(self) -> MTPopupOverlay:
        return self._overlay_widget

    def page_state(self) -> tuple[str, ...]:
        state = ()
        
        page_controller = self._page_controller
        while page_controller is not None:
            state += (self._page_controller.current.name,)
            page_controller = self._page_controller.parent_controller

        return state
