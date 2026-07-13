from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTSwitchSetting,
    MTWidget,
)
from src.config.enums import ConfigKey, ConfigLoaderKey as CLKey


class SettingsMiscPage(MTWidget):
    def __init__(self, *, config_loader: ConfigLoader, config: Config) -> None:
        super().__init__()
        self._config_loader = config_loader
        self._config = config

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="DBGR",
                obj_name="Settings_Misc_Debugger",
                widgets=[
                    MTSwitchSetting(
                        config=self._config_loader,
                        tr_key="DEBUG",
                        cfg_key=CLKey.MISC_DEBUGGER_DEBUG,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=self._config_loader,
                        tr_key="INFO",
                        cfg_key=CLKey.MISC_DEBUGGER_INFO,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=self._config_loader,
                        tr_key="WARNING",
                        cfg_key=CLKey.MISC_DEBUGGER_WARNING,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=self._config_loader,
                        tr_key="ERROR",
                        cfg_key=CLKey.MISC_DEBUGGER_ERROR,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=self._config_loader,
                        tr_key="EXCEPTION",
                        cfg_key=CLKey.MISC_DEBUGGER_EXCEPTION,
                        default=False,
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="DS_RPC",
                obj_name="Settings_Misc_Discord_RPC",
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="ENBL_DS_RPC",
                        cfg_key=ConfigKey.OUTPUTS_DISCORD_RICH_PRESENCE,
                        default=False,
                    ),
                ],
            ),
        ]

        main_layout.addWidget(MTColumnsSetting(tabs, 2, obj_name="Settings_Misc"))
