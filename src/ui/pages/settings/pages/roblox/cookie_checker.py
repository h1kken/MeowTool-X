from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTSliderSetting, MTSwitchSetting, MTLineEditSetting
from src.ui.widgets.roblox.cookie_checker import MTCookieCheckerFieldSetting
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN
from src.services.roblox.constants import ROBLOX_COOKIE_CHECKER_MAIN_FIELDS

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsRobloxCookieCheckerPage(BasePage):
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
        
        self._main_field_switches: list[MTCookieCheckerFieldSetting] = []

        tabs = [
            MTCollapsibleContainer(
                tr_key='GNRL',
                obj_name='Settings_Roblox_Cookie_Checker',
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Firstly Check For Valid',
                        tr_key='FRST_CHCK_FR_VLD',
                    ),
                    MTSliderSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Valid Threads',
                        tr_key='VLD_THRDS',
                        min_value=1,
                        max_value=1000,
                    ),
                    MTSliderSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Main Threads',
                        tr_key='MAIN_THRDS',
                        min_value=1,
                        max_value=250,
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Output Filename Like Input',
                        tr_key='OTPT_FLNM_LK_INPT',
                    ),
                    MTLineEditSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Output Filename',
                        tr_key='OTPT_FLNM',
                    ),
                    MTSwitchSetting(
                        config=config,
                        cfg_key='Roblox>Cookie Checker>Move Cookie To The Next Line',
                        tr_key='MV_C_TO_THE_NXT_LN',
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key='CHCKS',
                obj_name='Settings_Roblox_Cookie_Checker_Main',
                widgets=self._build_main_fields_widgets(),
            ),
        ]

        columns_widget = MTColumnsSetting(tabs=tabs, obj_name='Settings_Roblox_Cookie_Checker')
        self._layout.addWidget(columns_widget)

    def _build_main_fields_widgets(self) -> list[QWidget]:
        widgets: list[QWidget] = [
            MTButton(
                tr_key='ENBL_ALL_DSBL_ALL',
                obj_name='Settings_Roblox_Cookie_Checker_Main_Change_All_Button',
                action=self._change_main_fields_state,
            )
        ]
        self._main_field_switches.clear()
        for field in ROBLOX_COOKIE_CHECKER_MAIN_FIELDS:
            normalized_field_name = self._normalize_object_token(field)
            obj_name = f'Settings_Roblox_Cookie_Checker_Main_{normalized_field_name}'
            
            switch = MTCookieCheckerFieldSetting(
                config=self._config,
                cfg_key=f'Roblox>Cookie Checker>Main>{field}>Enabled',
                tr_key=f'FLD_{normalized_field_name.upper()}',
                obj_name=obj_name,
                field_name=field,
            )
            self._main_field_switches.append(switch)
            widgets.append(switch)
        return widgets

    @staticmethod
    def _normalize_object_token(value: str) -> str:
        return '_'.join(part for part in NORMALIZE_QT_KEY_PATTERN.sub('_', str(value)).split('_') if part)

    def _change_main_fields_state(self) -> None:
        to_state = False
        if not all(switch.is_checked() for switch in self._main_field_switches):
            to_state = True

        updates = {
            f'Roblox>Cookie Checker>Main>{field}>Enabled': to_state
                for field in ROBLOX_COOKIE_CHECKER_MAIN_FIELDS
        }
        self._config.set_many(updates)
        for switch in self._main_field_switches:
            switch.set_checked(to_state, emit_signal=False)
