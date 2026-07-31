from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget, QSizePolicy

from src.ui.windows.types import PageSpec
from src.ui.pages.base import BasePage
from src.ui.controllers import PageController
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.pages.settings.pages import (
    SettingsMainPage,
    SettingsOutputsPage,
    SettingsProxyPage,
    SettingsRobloxPage,
    SettingsMiscPage,
    SettingsConfigPage,
    SettingsThemePage,
)
from src.ui.types import PageState
from src.ui.widgets.common import MTButton, MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


_PAGES: list[PageSpec | None] = [
    (None, 'Main',    'MAIN',    SettingsMainPage),
    (None, 'Outputs', 'OUTPUTS', SettingsOutputsPage),
    (None, 'Proxy',   'PROXY',   SettingsProxyPage),
    (None, 'Roblox',  'ROBLOX',  SettingsRobloxPage),
    (None, 'Misc',    'MISC',    SettingsMiscPage),
    (None, 'Config',  'CONFIG',  SettingsConfigPage),
    (None, 'Theme',   'THEME',   SettingsThemePage),
]


class SettingsPage(BasePage):
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
        
        self._tab_names_by_key: dict[str, str] = {}
        self._pages_by_key: dict[str, MTWidget] = {}

        self._layout = create_layout(LayoutType.VBOX, self)
        main_widget = MTWidget(obj_name='Settings_Main_Tabs_Widget')
        self._layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, main_widget)

        self._page_controller = PageController(self._layout)

        for page_spec in _PAGES:
            if page_spec is None:
                tabs_layout.addStretch()
                continue
            
            _icon_name, obj_name, tr_key, page_class = page_spec
            
            self._tab_names_by_key[tr_key] = obj_name
            
            page = page_class(config=self._config)
            self._pages_by_key[tr_key] = page
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            if isinstance(page, (SettingsProxyPage, SettingsRobloxPage)):
                page.pageChanged.connect(self._emit_page_changed)

            self._page_controller.add_page(tr_key, page, obj_name=f'Settings_{obj_name}_Page')

            btn = MTButton(tr_key=tr_key, obj_name=f'Settings_{obj_name}_Tab_Button')
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)

        tabs_layout.addStretch()
        self._page_controller.show(_PAGES[0][2]) # type: ignore[index] | show the first page
        self._page_controller.pageChanged.emit()
        self._emit_page_changed()

    def current_page(self) -> PageState:
        state: PageState = {'main': 'Settings'}
        top_key = self._page_controller.current_key()
        if not isinstance(top_key, str):
            return state

        top_label = self._tab_names_by_key.get(top_key, top_key)
        state['inner'] = (top_label,)
        page = self._pages_by_key.get(top_key)
        if isinstance(page, (SettingsProxyPage, SettingsRobloxPage)):
            inner = page.current_page_inner()
            if inner:
                state['inner'] = (top_label, *inner)
        return state

    def _emit_page_changed(self) -> None:
        self._page_controller.pageChanged.emit(self.current_page())
