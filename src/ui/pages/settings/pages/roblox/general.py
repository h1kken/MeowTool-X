from src.config.manager import config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTComboBoxSetting,
    MTWidget,
    MTSwitchSetting,
    MTTextSetting,
)


class SettingsRobloxGeneralPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="Cookie parse",
                obj_name="Settings_Roblox_General_Cookie_Parse",
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        tr_key="Add symbols between warning and cookie",
                        cfg_key="Roblox>General>Add Symbols Between Warning And Cookie",
                        default=False,
                    ),
                    MTTextSetting(
                        config=config,
                        tr_key="Symbols between warning and cookie",
                        cfg_key="Roblox>General>Symbols Between Warning And Cookie",
                        default="CAEaAhAB.",
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="Proxy",
                obj_name="Settings_Roblox_General_Proxy",
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        tr_key="Use proxy",
                        cfg_key="Roblox>General>Proxy>Use Proxy",
                        default=False,
                    ),
                    MTComboBoxSetting(
                        config=config,
                        tr_key="Auto protocol if not specified",
                        cfg_key="Roblox>General>Proxy>Auto Protocol If Not Specified",
                        items=["http", "https", "socks4", "socks5"],
                        default="http",
                    ),
                ],
            ),
        ]

        main_layout.addWidget(
            MTColumnsSetting(tabs, 2, obj_name="Settings_Roblox_General_Columns")
        )
