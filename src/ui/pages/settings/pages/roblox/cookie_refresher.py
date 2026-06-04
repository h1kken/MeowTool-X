from src.config.manager import config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTSwitchSetting,
)


class SettingsRobloxCookieRefresherPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_Roblox_Cookie_Refresher",
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        tr_key="BRK_OLD_C",
                        cfg_key="Roblox>Cookie Refresher>Break Old Cookies",
                        default=False,
                    ),
                ],
            ),
        ]

        main_layout.addWidget(
            MTColumnsSetting(tabs, 2, obj_name="Settings_Roblox_Cookie_Refresher")
        )
