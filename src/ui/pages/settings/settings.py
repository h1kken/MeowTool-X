from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

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
from src.ui.widgets.common import MTButton, MTWidget

if t.TYPE_CHECKING:
    from src.config import Config


_PAGES: tuple[PageSpec | None, ...] = (
    PageSpec(SettingsMainPage,    'MAIN',    'Main'),
    PageSpec(SettingsOutputsPage, 'OUTPUTS', 'Outputs'),
    PageSpec(SettingsProxyPage,   'PROXY',   'Proxy', has_page_controller=True),
    PageSpec(SettingsRobloxPage,  'ROBLOX',  'Roblox', has_page_controller=True),
    PageSpec(SettingsMiscPage,    'MISC',    'Misc'),
    PageSpec(SettingsConfigPage,  'CONFIG',  'Config'),
    PageSpec(SettingsThemePage,   'THEME',   'Theme'),
    None,
)


class SettingsPage(BasePage):
    _OBJECT_NAME = 'Settings'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        parent_page_controller: PageController,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsPage._OBJECT_NAME))
        self._parent_page_controller = parent_page_controller

        self._tab_names_by_key: dict[str, str] = {}
        
        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._tabs_widget = MTWidget(obj_name=(obj_name, 'Tabs'))
        self._tabs_layout = create_layout(LayoutType.HBOX, self._tabs_widget)
        self._main_layout.addWidget(self._tabs_widget)

        self._page_controller = PageController(self._main_layout, parent_page_controller=self._parent_page_controller)

        for spec in _PAGES:
            if spec is None:
                self._tabs_layout.addStretch()
                continue
                        
            name = spec.obj_name.replace('_', ' ')
            self._tab_names_by_key[spec.tr_key] = name
            
            if spec.has_page_controller:
                page = spec.page_class(
                    config=self._config,
                    parent_page_controller=self._page_controller, # type: ignore[call-arg]
                    obj_name=(obj_name, SettingsPage._OBJECT_NAME,),
                )
            else:
                page = spec.page_class(
                    config=self._config,
                    obj_name=(obj_name, SettingsPage._OBJECT_NAME,),
                )
                        
            button = MTButton(tr_key=spec.tr_key, obj_name=(SettingsPage._OBJECT_NAME, spec.obj_name, 'Tab'))
            self._tabs_layout.addWidget(button)
            
            self._page_controller.add_page(
                key=spec.tr_key,
                name=name,
                page=page,
                button=button,
            )
