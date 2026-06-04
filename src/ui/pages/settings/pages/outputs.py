from src.config.manager import config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTWidget,
    MTTextSetting,
    MTSwitchSetting,
)


class SettingsOutputsPage(MTWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="TG_BOT",
                obj_name="Settings_Telegram_Bot",
                widgets=[
                    MTTextSetting(
                        config=config,
                        tr_key="TKN",
                        cfg_key="Outputs>Telegram Bot>Token",
                        default="",
                    ),
                    MTTextSetting(
                        config=config,
                        tr_key="CHT_ID",
                        cfg_key="Outputs>Telegram Bot>Chat ID",
                        default="",
                    ),
                    MTSwitchSetting(
                        config=config,
                        tr_key="SND_RSLTS_TO_TG_BOT",
                        cfg_key="Outputs>Telegram Bot>Send Results To Telegram Bot",
                        default=False,
                    ),
                    # TODO: Test Meow
                ],
            ),
            MTCollapsibleContainer(
                tr_key="DS_WBHK",
                obj_name="Settings_Discord_Webhook",
                widgets=[
                    MTTextSetting(
                        config=config,
                        tr_key="URL",
                        cfg_key="Outputs>Discord Webhook>URL",
                        default="",
                    ),
                    MTSwitchSetting(
                        config=config,
                        tr_key="SND_RSLTS_TO_DS_WBHK",
                        cfg_key="Outputs>Discord Webhook>Send Results To Discord Webhook",
                        default=False,
                    ),
                    # TODO: Test Meow
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs, 2, obj_name="Settings_Outputs")
        main_layout.addWidget(columns_widget)
