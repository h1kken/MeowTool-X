from __future__ import annotations

import typing as t

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QSizePolicy

from src.ui.windows.types import PageSpec
from src.ui.pages.base import BasePage
from src.ui.controllers import PageController
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.pages.settings.pages.roblox import (
    SettingsRobloxCookieSorterPage,
    SettingsRobloxCookieCheckerPage,
    SettingsRobloxCookieRefresherPage,
)
from src.ui.widgets.common import MTButton, MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


_PAGES: list[PageSpec | None] = [
    (None, 'Cookie_Sorter',    'CK_SRTR',   SettingsRobloxCookieSorterPage),
    (None, 'Cookie_Checker',   'CK_CHCKR',  SettingsRobloxCookieCheckerPage),
    (None, 'Cookie_Refresher', 'CK_RFRSHR', SettingsRobloxCookieRefresherPage),
    None,
]


class SettingsRobloxPage(BasePage):
    pageChanged = Signal()

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
        
        self._layout = create_layout(LayoutType.VBOX, self)
        
        self._tab_labels_by_key: dict[str, str] = {}

        main_widget = MTWidget(obj_name='Settings_Roblox_Tabs_Widget')
        self._layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, main_widget)

        self._page_controller = PageController(self._layout)

        for page_spec in _PAGES:
            if page_spec is None:
                tabs_layout.addStretch()
                continue

            _icon_name, obj_name, tr_key, page_class = page_spec
            
            self._tab_labels_by_key[tr_key] = str(obj_name).replace('_', ' ')

            page = page_class(config=self._config)
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._page_controller.add_page(tr_key, page, obj_name=f'Settings_Roblox_{obj_name}_Page')

            btn = MTButton(tr_key=tr_key, obj_name=f'Settings_Roblox_{obj_name}_Tab_Button')
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)

        self._page_controller.show(_PAGES[0][2]) # type: ignore[index] | show the first page
        self._page_controller.pageChanged.emit()

    def current_page_inner(self) -> tuple[str, ...]:
        key = self._page_controller.current_key()
        if not isinstance(key, str):
            return ()

        label = self._tab_labels_by_key.get(key, key)
        return (label,) if label else ()
