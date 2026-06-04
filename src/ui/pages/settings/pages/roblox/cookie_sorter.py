from src.config.manager import config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTTextSetting,
)


class SettingsRobloxCookieSorterPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_Roblox_Cookie_Sorter",
                widgets=[
                    MTTextSetting(
                        config=config,
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
