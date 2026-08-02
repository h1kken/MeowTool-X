from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTComboBoxSetting, MTSwitchSetting, MTLineEditSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxGeneralPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(parent, config=config, obj_name=obj_name)
        
        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._settings = [
            MTCollapsibleContainer(
                tr_key='Cookie parse',
                obj_name='Settings_Roblox_General_Cookie_Parse',
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Add Symbols Between Warning And Cookie',
                        tr_key='Add symbols between warning and cookie',
                    ),
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Symbols Between Warning And Cookie',
                        tr_key='Symbols between warning and cookie',
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key='Proxy',
                obj_name='Settings_Roblox_General_Proxy',
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Proxy>Use Proxy',
                        tr_key='Use proxy',
                    ),
                    MTComboBoxSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Proxy>Auto Protocol If Not Specified',
                        tr_key='Auto protocol if not specified',
                        items=['http', 'https', 'socks4', 'socks5'],
                        default='http',
                    ),
                ],
            ),
        ]

        self._columns_widget = MTColumnsSetting(obj_name='Settings_Roblox_General_Columns', tabs=self._settings)
        self._main_layout.addWidget(self._columns_widget)
