from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTSwitchSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxCookieRefresherPage(BasePage):
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
                tr_key='GNRL',
                obj_name='Settings_Roblox_Cookie_Refresher',
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Refresher>Break Old Cookies',
                        tr_key='BRK_OLD_C',
                    ),
                ],
            ),
        ]

        self._layout.addWidget(MTColumnsSetting(tabs=tabs, obj_name='Settings_Roblox_Cookie_Refresher'))
