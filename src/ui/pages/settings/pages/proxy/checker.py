from src.config.manager import config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTSliderSetting,
    MTSwitchSetting,
)


class SettingsProxyCheckerPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_Proxy_Checker_General",
                widgets=[
                    MTSliderSetting(
                        config=config,
                        tr_key="MAIN_THRDS",
                        cfg_key="Proxy>Checker>General>Main Threads",
                        min_value=1,
                        max_value=1000,
                        default=50,
                    ),
                    MTSliderSetting(
                        config=config,
                        tr_key="MAX_WT_RESP",
                        cfg_key="Proxy>Checker>General>Maximum Wait Response",
                        min_value=1,
                        max_value=60,
                        default=10,
                    ),
                    MTSwitchSetting(
                        config=config,
                        tr_key="SV_GD_IN_CSTM_FL",
                        cfg_key="Proxy>Checker>General>Save Good In Custom File",
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=config,
                        tr_key="SV_WTOUT_PRTCL",
                        cfg_key="Proxy>Checker>General>Save Without Protocol",
                        default=False,
                    ),
                ],
            ),
        ]

        main_layout.addWidget(
            MTColumnsSetting(tabs, 2, obj_name="Settings_Proxy_Checker")
        )
