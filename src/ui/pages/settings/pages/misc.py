from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTSwitchSetting
from src.config.enums import (
    ConfigKey as CKey,
    ConfigLoaderKey as CLKey
)

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsMiscPage(BasePage):
    _OBJECT_NAME = 'Misc'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsMiscPage._OBJECT_NAME))

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
                tr=TrKey(key='DBGR'),
                obj_name=(obj_name, 'Debugger'),
                widgets=[
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_DEBUG,
                        tr=TrKey(key='DEBUG'),
                        obj_name=(obj_name, 'Debug')
                    ),
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_INFO,
                        tr=TrKey(key='INFO'),
                        obj_name=(obj_name, 'Info')
                    ),
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_WARNING,
                        tr=TrKey(key='WARNING'),
                        obj_name=(obj_name, 'Warning')
                    ),
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_ERROR,
                        tr=TrKey(key='ERROR'),
                        obj_name=(obj_name, 'Error')
                    ),
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CLKey.MISC_DEBUGGER_EXCEPTION,
                        tr=TrKey(key='EXCEPTION'),
                        obj_name=(obj_name, 'Exception')
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr=TrKey(key='DS_RPC'),
                obj_name=(obj_name, 'Discord_RPC'),
                widgets=[
                    MTSwitchSetting(
                        config=self._config.loader,
                        cfg_key=CKey.MISC_DISCORD_RPC,
                        tr=TrKey(key='ENBL'),
                        obj_name=(obj_name, 'Enabled'),
                    ),
                ],
            ),
        ]
