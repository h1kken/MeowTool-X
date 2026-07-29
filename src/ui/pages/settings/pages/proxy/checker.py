from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTCollapsibleContainer, MTColumnsSetting, MTSliderSetting, MTSwitchSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsProxyCheckerPage(BasePage):
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
                tr_key='GNRL',
                obj_name='Settings_Proxy_Checker_General',
                widgets=[
                    MTSliderSetting(
                        config=config,
                        cfg_key='Proxy>Checker>General>Main Threads',
                        tr_key='MAIN_THRDS',
                        min_value=1,
                        max_value=1000,
                    ),
                    MTSliderSetting(
                        config=config,
                        cfg_key='Proxy>Checker>General>Maximum Wait Response',
                        tr_key='MAX_WT_RESP',
                        min_value=1,
                        max_value=60,
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Proxy>Checker>General>Save Good In Custom File',
                        tr_key='SV_GD_IN_CSTM_FL',
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Proxy>Checker>General>Save Without Protocol',
                        tr_key='SV_WTOUT_PRTCL',
                    ),
                ],
            ),
        ]

        self._layout.addWidget(MTColumnsSetting(tabs=tabs, obj_name='Settings_Proxy_Checker'))
