from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTCollapsibleContainer, MTColumnsSetting, MTTextSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxCookieSorterPage(BasePage):
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
                obj_name='Settings_Roblox_Cookie_Sorter',
                widgets=[
                    MTTextSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Sorter>Output Filename',
                        tr_key='OTPT_FLNM',
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs=tabs, columns=2, obj_name='Settings_Roblox_Cookie_Sorter')
        self._layout.addWidget(columns_widget)
