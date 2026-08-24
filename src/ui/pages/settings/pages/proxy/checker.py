from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.translation import Translation as Tr
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTSliderSetting, MTSwitchSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsProxyCheckerPage(BasePage):
    _OBJECT_NAME = 'Checker'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsProxyCheckerPage._OBJECT_NAME))

        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._columns_widget = MTColumnsSetting(obj_name=(obj_name,), tabs=self._create_settings())
        self._main_layout.addWidget(self._columns_widget)

    def _create_settings(self) -> list[MTCollapsibleContainer]:
        obj_name = self.objectName()
        return [
            MTCollapsibleContainer(
                tr=Tr(key='GNRL'),
                obj_name=(obj_name, 'General'),
                widgets=[
                    MTSliderSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Main Threads',
                        tr=Tr(key='MN_THRDS'),
                        obj_name=(obj_name, 'Main_Threads'),
                        min_value=1,
                        max_value=1000,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Maximum Wait Response',
                        tr=Tr(key='MX_WT_RESP'),
                        obj_name=(obj_name, 'Maximum_Wait_Response'),
                        min_value=1,
                        max_value=60,
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Save Good In Custom File',
                        tr=Tr(key='SV_GD_IN_CSTM_FL'),
                        obj_name=(obj_name, 'Save_Good_In_Custom_File'),
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Proxy>Checker>Save Without Protocol',
                        tr=Tr(key='SV_WTOUT_PRTCL'),
                        obj_name=(obj_name, 'Save_Without_Protocol'),
                    ),
                ],
            ),
        ]
