from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTLineEditSetting, MTSwitchSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsOutputsPage(BasePage):
    _OBJECT_NAME = 'Outputs'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsOutputsPage._OBJECT_NAME))

        self._build_ui()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._columns_widget = MTColumnsSetting(obj_name=(obj_name,), tabs=self._create_settings())
        self._main_layout.addWidget(self._columns_widget)

    def _create_settings(self) -> list[MTCollapsibleContainer]:
        obj_name = self.objectName()
        return [
            MTCollapsibleContainer(
                tr_key='TG_BOT',
                obj_name=(SettingsOutputsPage._OBJECT_NAME, 'Telegram_Bot'),
                widgets=[
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Outputs>Telegram Bot>Token',
                        tr_key='TKN',
                        obj_name=(obj_name, 'Token')
                    ),
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Outputs>Telegram Bot>Chat ID',
                        tr_key='CHT_ID',
                        obj_name=(obj_name, 'Chat_ID')
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Outputs>Telegram Bot>Send Results To Telegram Bot',
                        tr_key='SND_RSLTS_TO_TG_BOT',
                        obj_name=(obj_name, 'Send_Results_To_Telegram_Bot')
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key='DS_WBHK',
                obj_name=(SettingsOutputsPage._OBJECT_NAME, 'Discord_Webhook'),
                widgets=[
                    MTLineEditSetting(
                        config=self._config,
                        cfg_key='Outputs>Discord Webhook>URL',
                        tr_key='URL',
                        obj_name=(obj_name, 'URL')
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        cfg_key='Outputs>Discord Webhook>Send Results To Discord Webhook',
                        tr_key='SND_RSLTS_TO_DS_WBHK',
                        obj_name=(obj_name, 'Send_Results_To_Discord_Webhook')
                    ),
                ],
            ),
        ]