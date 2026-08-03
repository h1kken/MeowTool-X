from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow

from src.app.constants import PROGRAM_TITLE
from src.app.paths import PATH_SIDEBAR_ICONS_SRC
from src.ui.constants import WINDOW_X, WINDOW_Y
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
    
    def __init__(
        self,
        config: Config
    ) -> None:
        super().__init__()
        self._config = config
        
        self._tab_names_by_key: dict[str, str] = {}
        
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        self.setWindowTitle(PROGRAM_TITLE)
        self.resize(WINDOW_X, WINDOW_Y)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setObjectName('Main_Window')

        self._central_widget = MTWidget(obj_name='Main_Window_Central_Widget')
        self.setCentralWidget(self._central_widget)
        
        self._central_layout = create_layout(LayoutType.VBOX, self._central_widget)
        self._header = MTWindowHeader(self)
        self._central_layout.addWidget(self._header)

        self._body_widget = MTWidget(obj_name='Main_Window_Body_Widget')
        self._central_layout.addWidget(self._body_widget, stretch=1)
        
        self._body_layout = create_layout(LayoutType.HBOX, self._body_widget)
        self._sidebar_widget = MTWidget(obj_name='Sidebar_Widget')
        self._body_layout.addWidget(self._sidebar_widget)
        
        self._sidebar_layout = create_layout(LayoutType.VBOX, self._sidebar_widget)
        self._sidebar_layout.addWidget(MTImage(self._sidebar_widget)) # TODO: is it correct?
        
        self._main_content = MTWidget(obj_name='Main_Content_Widget')
        self._body_layout.addWidget(self._main_content, stretch=1)

        self._pages_layout = create_layout(LayoutType.VBOX, self._main_content)
        self._page_controller = PageController(self._pages_layout)

        for spec in _PAGES:
            if spec is None:
                self._sidebar_layout.addStretch()
                continue
            
            name = str(spec.obj_name).replace('_', ' ')
            self._tab_names_by_key[spec.tr_key] = name
            
            obj_name = f'Main_{spec.obj_name}_Page'
            
            if spec.has_page_controller:
                page = spec.page_class(
                    config=self._config,
                    parent_page_controller=self._page_controller, # type: ignore[call-arg]
                    obj_name=obj_name,
                )
            else:
                page = spec.page_class(
                    config=self._config,
                    obj_name=obj_name,
                )
                
            button = MTButton(tr_key=spec.tr_key, obj_name=f'Sidebar_{spec.obj_name}_Button')
            button.set_icon(source=str(PATH_SIDEBAR_ICONS_SRC / spec.icon) if spec.icon else None)
            self._sidebar_layout.addWidget(button)
            
            self._page_controller.add_page(
                key=spec.tr_key,
                name=name,
                page=page,
                button=button,
            )
            
    def _connect_signals(self) -> None:
        self._page_controller.pageChanged.connect(self.pageChanged.emit)

    def page_state(self) -> tuple[str, ...]:
        state = ()
        
        page_controller = self._page_controller
        
        while page_controller is not None:
            state += (self._page_controller.current.name,)
            page_controller = self._page_controller.parent_controller

        return state
