from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTButtonSetting,
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTSliderSetting,
    MTSwitchSetting,
    MTTextSetting,
    MTWidget,
)
from src.ui.widgets.roblox.cookie_checker import MTCookieCheckerFieldSetting
from src.services.roblox.constants import ROBLOX_COOKIE_CHECKER_MAIN_FIELDS
from src.ui.regexes import NORMALIZE_QT_KEY_PATTERN

class SettingsRobloxCookieCheckerPage(MTWidget):
    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config
        self._main_field_switches: list[MTCookieCheckerFieldSetting] = []

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_Roblox_Cookie_Checker",
                widgets=[
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="FRST_CHCK_FR_VLD",
                        cfg_key="Roblox>Cookie Checker>Firstly Check For Valid",
                        default=False,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        tr_key="VLD_THRDS",
                        cfg_key="Roblox>Cookie Checker>Valid Threads",
                        min_value=1,
                        max_value=1000,
                        default=50,
                    ),
                    MTSliderSetting(
                        config=self._config,
                        tr_key="MAIN_THRDS",
                        cfg_key="Roblox>Cookie Checker>Main Threads",
                        min_value=1,
                        max_value=250,
                        default=25,
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="OTPT_FLNM_LK_INPT",
                        cfg_key="Roblox>Cookie Checker>Output Filename Like Input",
                        default=False,
                    ),
                    MTTextSetting(
                        config=self._config,
                        tr_key="OTPT_FLNM",
                        cfg_key="Roblox>Cookie Checker>Output Filename",
                        default="output",
                    ),
                    MTSwitchSetting(
                        config=self._config,
                        tr_key="MV_C_TO_THE_NXT_LN",
                        cfg_key="Roblox>Cookie Checker>Move Cookie To The Next Line",
                        default=False,
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="CHCKS",
                obj_name="Settings_Roblox_Cookie_Checker_Main",
                widgets=self._build_main_fields_widgets(),
            ),
        ]

        main_layout.addWidget(
            MTColumnsSetting(tabs, 2, obj_name="Settings_Roblox_Cookie_Checker")
        )

    def _build_main_fields_widgets(self) -> list[QWidget]:
        widgets: list[QWidget] = [
            MTButtonSetting(
                self._change_main_fields_state,
                tr_key="ENBL_ALL_DSBL_ALL",
                obj_name="Settings_Roblox_Cookie_Checker_Main_Change_All_Button",
            )
        ]
        self._main_field_switches.clear()
        for field in ROBLOX_COOKIE_CHECKER_MAIN_FIELDS:
            normalized_field_name = self._normalize_object_token(field)
            field_obj_name = f"Settings_Roblox_Cookie_Checker_Main_{normalized_field_name}"
            
            switch = MTCookieCheckerFieldSetting(
                config=self._config,
                field_name=field,
                tr_key=f"FLD_{normalized_field_name.upper()}",
                cfg_key=f"Roblox>Cookie Checker>Main>{field}>Enabled",
                default=False,
                obj_name=field_obj_name,
            )
            self._main_field_switches.append(switch)
            widgets.append(switch)
        return widgets

    @staticmethod
    def _normalize_object_token(value: str) -> str:
        return "_".join(
            part
                for part in NORMALIZE_QT_KEY_PATTERN.sub("_", str(value)).split("_")
                    if part
        )

    def _change_main_fields_state(self) -> None:
        to_state = False
        if not all(switch.is_checked() for switch in self._main_field_switches):
            to_state = True

        updates = {
            f"Roblox>Cookie Checker>Main>{field}>Enabled": to_state
                for field in ROBLOX_COOKIE_CHECKER_MAIN_FIELDS
        }
        self._config.set_many(updates)
        for switch in self._main_field_switches:
            switch.set_checked(to_state, emit_signal=False)
