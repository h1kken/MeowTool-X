from __future__ import annotations

from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTTextSetting,
)


class SettingsRobloxCookieSorterPage(MTWidget):
    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_Roblox_Cookie_Sorter",
                widgets=[
                    MTTextSetting(
                        config=self._config,
                        tr_key="OTPT_FLNM",
                        cfg_key="Roblox>Cookie Sorter>Output Filename",
                        default="output",
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(
            tabs, 2, obj_name="Settings_Roblox_Cookie_Sorter"
        )
        main_layout.addWidget(columns_widget)
