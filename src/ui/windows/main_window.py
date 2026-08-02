from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from src.app.paths import PATH_SIDEBAR_ICONS_SRC
from src.ui.constants import WINDOW_X, WINDOW_Y
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
from src.ui.types import PageState
from src.ui.widgets.common import MTButton, MTWidget, MTImage
from src.ui.windows.types import PageSpec
from src.ui.windows.window_header import MTWindowHeader

if t.TYPE_CHECKING:
    from src.config import Config


_PAGES: list[PageSpec | None] = [
    ('checker.svg',   'Proxy_Checker',           'CHCKR',     ProxyCheckerPage),
    ('sorter.svg',    'Roblox_Cookie_Sorter',    'CK_SRTR',   RobloxCookieSorterPage),
    ('checker.svg',   'Roblox_Cookie_Checker',   'CK_CHCKR',  RobloxCookieCheckerPage),
    ('refresher.svg', 'Roblox_Cookie_Refresher', 'CK_RFRSHR', RobloxCookieRefresherPage),
    None,
    ('settings.svg',  'Settings',                'STNGS',     SettingsPage),
]


class MainWindow(QMainWindow):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
                
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName('Main_Window')
        self.resize(WINDOW_X, WINDOW_Y)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        central_widget = MTWidget(obj_name='Main_Window_Central_Widget')
        self.setCentralWidget(central_widget)
        central_layout = create_layout(LayoutType.VBOX, central_widget)
        
        header_widget = MTWindowHeader(self)

        body_widget = MTWidget(obj_name='Main_Window_Body_Widget')
        body_layout = create_layout(LayoutType.HBOX, body_widget)
        
        sidebar_widget = MTWidget(obj_name='Sidebar_Widget')
        sidebar_layout = create_layout(LayoutType.VBOX, sidebar_widget)
        sidebar_layout.addWidget(MTImage(sidebar_widget))
        
        main_content = MTWidget(obj_name='Main_Content_Widget')
        pages_layout = create_layout(LayoutType.VBOX, main_content)
        
        central_layout.addWidget(header_widget)
        central_layout.addWidget(body_widget, stretch=1)
        body_layout.addWidget(sidebar_widget)
        body_layout.addWidget(main_content)

        self._page_controller = PageController(pages_layout)

        for page_spec in _PAGES:
            if page_spec is None:
                sidebar_layout.addStretch()
                continue

            icon_name, obj_name, tr_key, page_class = page_spec
            
            page = page_class(config=self._config)
            page_label = obj_name.replace('_', ' ')
            self._page_controller.add_page(tr_key, page, obj_name=f'Main_{obj_name}_Page')

            button = MTButton(tr_key=tr_key, obj_name=f'Sidebar_{obj_name}_Button')
            button.set_icon(source=str(PATH_SIDEBAR_ICONS_SRC / icon_name) if icon_name else None)
            self._page_controller.bind_tab(tr_key, button)

            if isinstance(page, SettingsPage):
                button.clicked.connect(lambda _checked=False, settings=page: self._set_page_state(settings.current_page()))
            else:
                button.clicked.connect(lambda _checked=False, label=page_label: self._set_page_state({'main': label}))

            sidebar_layout.addWidget(button)

        self._page_controller.show(_PAGES[0][2]) # type: ignore[index] | show the first page
        self._page_controller.pageChanged.emit()
        self._set_page_state({'main': _PAGES[0][1]}) # type: ignore[index]

    def _set_page_state(self, state: PageState) -> None:
        normalized: PageState = {'main': state.get('main', '')}
        inner = state.get('inner')
        if isinstance(inner, tuple):
            normalized_inner = tuple(
                value
                    for value in (str(part).strip() for part in inner)
                        if value
            )
            if normalized_inner:
                normalized['inner'] = normalized_inner

        if normalized == self._page_state:
            return

        self._page_state = normalized
        # self.pageChanged.emit(normalized)

    def _on_settings_page_changed(self, state: PageState) -> None:
        if self._page_controller.current_key() == 'STNGS':
            self._set_page_state(state)

    def current_state(self) -> PageState:
        return self._page_state.copy()
