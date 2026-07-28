from __future__ import annotations

from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTTextSetting,
    MTSwitchSetting,
)


class SettingsOutputsPage(MTWidget):
    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="TG_BOT",
                obj_name="Settings_Telegram_Bot",
                widgets=[
                    MTTextSetting(
                        tr_key="TKN",
                        cfg_key="Outputs>Telegram Bot>Token",
                    ),
                    MTTextSetting(
                        tr_key="CHT_ID",
                        cfg_key="Outputs>Telegram Bot>Chat ID",
                    ),
                    MTSwitchSetting(
                        tr_key="SND_RSLTS_TO_TG_BOT",
                        cfg_key="Outputs>Telegram Bot>Send Results To Telegram Bot",
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="DS_WBHK",
                obj_name="Settings_Discord_Webhook",
                widgets=[
                    MTTextSetting(
                        tr_key="URL",
                        cfg_key="Outputs>Discord Webhook>URL",
                    ),
                    MTSwitchSetting(
                        tr_key="SND_RSLTS_TO_DS_WBHK",
                        cfg_key="Outputs>Discord Webhook>Send Results To Discord Webhook",
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs, 2, obj_name="Settings_Outputs")
        main_layout.addWidget(columns_widget)
