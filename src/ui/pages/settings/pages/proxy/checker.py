from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTSliderSetting, MTSwitchSetting

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
        super().__init__(parent, config=config, obj_name=obj_name)

        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._settings = [
            MTCollapsibleContainer(
                tr_key='GNRL',
                obj_name='Settings_Proxy_Checker_General',
                widgets=[
                    MTSliderSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Main Threads',
                        tr_key='MAIN_THRDS',
                        min_value=1,
                        max_value=1000,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Maximum Wait Response',
                        tr_key='MAX_WT_RESP',
                        min_value=1,
                        max_value=60,
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Save Good In Custom File',
                        tr_key='SV_GD_IN_CSTM_FL',
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Save Without Protocol',
                        tr_key='SV_WTOUT_PRTCL',
                    ),
                ],
            ),
        ]

        self._columns_widget = MTColumnsSetting(obj_name='Settings_Proxy_Checker', tabs=self._settings)
        self._main_layout.addWidget(self._columns_widget)
