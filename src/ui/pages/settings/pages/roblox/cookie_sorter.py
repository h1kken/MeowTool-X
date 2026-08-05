from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTLineEditSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxCookieSorterPage(BasePage):
    _OBJECT_NAME = 'Cookie_Sorter'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, self._OBJECT_NAME))
        
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
                tr_key='GNRL',
                obj_name=(obj_name, 'Main'),
                widgets=[
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Roblox>Cookie Sorter>Output Filename',
                        tr_key='OTPT_FLNM',
                        obj_name=(obj_name, 'Output_Filename'),
                    ),
                ],
            ),
        ]
