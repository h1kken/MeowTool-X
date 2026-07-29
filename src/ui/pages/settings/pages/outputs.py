from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTCollapsibleContainer, MTColumnsSetting, MTTextSetting, MTSwitchSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsOutputsPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(
            parent,
            config=config,
            obj_name=obj_name
        )

        self._layout = create_layout(LayoutType.VBOX, self)

        tabs = [
            MTCollapsibleContainer(
                tr_key='TG_BOT',
                obj_name='Settings_Telegram_Bot',
                widgets=[
                    MTTextSetting(
                        config=config,
                        cfg_key='Outputs>Telegram Bot>Token',
                        tr_key='TKN',
                    ),
                    MTTextSetting(
                        config=config,
                        cfg_key='Outputs>Telegram Bot>Chat ID',
                        tr_key='CHT_ID',
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Outputs>Telegram Bot>Send Results To Telegram Bot',
                        tr_key='SND_RSLTS_TO_TG_BOT',
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key='DS_WBHK',
                obj_name='Settings_Discord_Webhook',
                widgets=[
                    MTTextSetting(
                        config=config,
                        cfg_key='Outputs>Discord Webhook>URL',
                        tr_key='URL',
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Outputs>Discord Webhook>Send Results To Discord Webhook',
                        tr_key='SND_RSLTS_TO_DS_WBHK',
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs=tabs, obj_name='Settings_Outputs')
        self._layout.addWidget(columns_widget)
