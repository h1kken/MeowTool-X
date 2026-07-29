from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTCollapsibleContainer, MTColumnsSetting, MTSwitchSetting
from src.config.enums import ConfigKey, ConfigLoaderKey as CLKey

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsMiscPage(BasePage):
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

        tabs = [
            MTCollapsibleContainer(
                tr_key='DBGR',
                obj_name='Settings_Misc_Debugger',
                widgets=[
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_DEBUG,
                        tr_key='DEBUG',
                    ),
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_INFO,
                        tr_key='INFO',
                    ),
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_WARNING,
                        tr_key='WARNING',
                    ),
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_ERROR,
                        tr_key='ERROR',
                    ),
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_EXCEPTION,
                        tr_key='EXCEPTION',
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key='DS_RPC',
                obj_name='Settings_Misc_Discord_RPC',
                widgets=[
                    MTSwitchSetting(
                        config=config.loader,
                        cfg_key=ConfigKey.OUTPUTS_DISCORD_RICH_PRESENCE,
                        tr_key='ENBL_DS_RPC',
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs=tabs, obj_name='Settings_Misc')
        self._layout.addWidget(columns_widget)
