from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTComboBoxSetting, MTSwitchSetting, MTLineEditSetting
from src.ui.widgets.types import ComboItem

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxGeneralPage(BasePage):
    _OBJECT_NAME = 'General'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsRobloxGeneralPage._OBJECT_NAME))
        
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
                tr=TrKey(key='CK_PRS'),
                obj_name=(obj_name, 'Main'),
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Add Symbols Between Warning And Cookie',
                        tr=TrKey(key='ADD_SMBLS_BTWN_WRNG_CCK'),
                        obj_name=(obj_name, 'Add_Symbols_Between_Warning_And_Cookie'),
                    ),
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Symbols Between Warning And Cookie',
                        tr=TrKey(key='SMBLS_BTWN_WRNG_AND_CCK'),
                        obj_name=(obj_name, 'Symbols_Between_Warning_And_Cookie'),
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr=TrKey(key='PRXY'),
                obj_name=(obj_name, 'Proxy'),
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Proxy>Use Proxy',
                        tr=TrKey(key='USE_PRXY'),
                        obj_name=(obj_name, 'Use_Proxy'),
                    ),
                    MTComboBoxSetting(
                        config=self._config,
                        cfg_key='Roblox>General>Proxy>Auto Protocol If Not Specified',
                        tr=TrKey(key='AT_PRTCL_IF_NT_SPCFD'),
                        obj_name=(obj_name, 'Auto_Protocol_If_Not_Specified'),
                        items=[ComboItem(TrKey(key=item)) for item in ('http', 'https', 'socks4', 'socks5')],
                    ),
                ],
            ),
        ]
