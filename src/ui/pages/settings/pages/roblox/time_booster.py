from __future__ import annotations

from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTWidget,
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTSliderSetting,
    MTSwitchSetting,
)


class SettingsRobloxTimeBoosterPage(MTWidget):
    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="Transaction analysis",
                obj_name="Settings_Roblox_Transaction_Analysis_Settings",
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="Firstly check for valid",
                        cfg_key="Roblox>Transaction Analysis>Firstly Check For Valid",
                        default=False,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        tr_key="Valid threads",
                        cfg_key="Roblox>Transaction Analysis>Valid Threads",
                        min_value=1,
                        max_value=1000,
                        default=50,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        tr_key="Main threads",
                        cfg_key="Roblox>Transaction Analysis>Main Threads",
                        min_value=1,
                        max_value=250,
                        default=25,
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="Indent by the longest name",
                        cfg_key="Roblox>Transaction Analysis>Indent By The Longest Name",
                        default=False,
                    ),
                ],
            ),
        ]

        main_layout.addWidget(
            MTColumnsSetting(tabs, 2, obj_name="Settings_Roblox_Time_Booster_Columns")
        )
