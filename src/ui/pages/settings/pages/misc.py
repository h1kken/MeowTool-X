from src.config.loader import config_loader
from src.config.manager import config
from src.theme.rainbow.palette import rainbow_palette_names
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTComboBoxSetting,
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTSliderSetting,
    MTWidget,
    MTSwitchSetting,
)
from src.config.enums import ConfigLoaderKey as CLKey


class SettingsMiscPage(MTWidget):
    def __init__(self):
        super().__init__()
        self._last_applied_rainbow_cycle_duration = self._read_rainbow_cycle_duration()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="DBGR",
                obj_name="Settings_Misc_Debugger",
                widgets=[
                    MTSwitchSetting(
                        config=config_loader,
                        tr_key="DEBUG",
                        cfg_key=CLKey.MISC_DEBUGGER_DEBUG,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=config_loader,
                        tr_key="INFO",
                        cfg_key=CLKey.MISC_DEBUGGER_INFO,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=config_loader,
                        tr_key="WARNING",
                        cfg_key=CLKey.MISC_DEBUGGER_WARNING,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=config_loader,
                        tr_key="ERROR",
                        cfg_key=CLKey.MISC_DEBUGGER_ERROR,
                        default=False,
                    ),
                    MTSwitchSetting(
                        config=config_loader,
                        tr_key="EXCEPTION",
                        cfg_key=CLKey.MISC_DEBUGGER_EXCEPTION,
                        default=False,
                    ),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="RNBW_MD",
                obj_name="Settings_Misc_Rainbow_Mode",
                widgets=[
                    self._build_rainbow_mode_setting(),
                    self._build_rainbow_cycle_duration_setting(),
                    self._build_rainbow_palette_setting(),
                ],
            ),
            MTCollapsibleContainer(
                tr_key="DS_RPC",
                obj_name="Settings_Misc_Discord_RPC",
                widgets=[
                    MTSwitchSetting(
                        config=config,
                        tr_key="ENBL_DS_RPC",
                        cfg_key="Outputs>Discord Presence>Enable Presence",
                        default=False,
                    ),
                ],
            ),
        ]

        main_layout.addWidget(MTColumnsSetting(tabs, 2, obj_name="Settings_Misc"))
        self._sync_rainbow_settings_state()

    def _build_rainbow_mode_setting(self) -> MTSwitchSetting:
        self._rainbow_mode_setting = MTSwitchSetting(
            config=config,
            tr_key="ENBLD",
            cfg_key="Misc>Rainbow Mode>Enabled",
            default=False,
        )
        self._rainbow_mode_setting.switch.toggled.connect(
            self._on_rainbow_mode_toggled,
        )
        return self._rainbow_mode_setting

    def _build_rainbow_cycle_duration_setting(self) -> MTSliderSetting:
        self._rainbow_cycle_duration_setting = MTSliderSetting(
            config,
            tr_key="RNBW_CCL_DRTN_MS",
            cfg_key="Misc>Rainbow Mode>Cycle Duration",
            min_value=1000,
            max_value=20000,
            default=5000,
        )
        self._rainbow_cycle_duration_setting.setObjectName(
            "Misc_Rainbow_Cycle_Duration_Slider_Setting"
        )
        self._rainbow_cycle_duration_setting.spin_box.editingFinished.connect(
            self._commit_rainbow_cycle_duration_change,
        )
        self._rainbow_cycle_duration_setting.slider.sliderReleased.connect(
            self._commit_rainbow_cycle_duration_change,
        )
        return self._rainbow_cycle_duration_setting

    def _build_rainbow_palette_setting(self) -> MTComboBoxSetting:
        self._rainbow_palette_setting = MTComboBoxSetting(
            config,
            tr_key="RNBW_PLT",
            cfg_key="Misc>Rainbow Mode>Palette",
            items=rainbow_palette_names(),
            default="Classic",
            on_changed=self._on_rainbow_palette_changed,
        )
        self._rainbow_palette_setting.setObjectName(
            "Misc_Rainbow_Mode_Rainbow_Palette_ComboBox_Setting"
        )
        return self._rainbow_palette_setting

    def _is_rainbow_mode_enabled(self) -> bool:
        return bool(config.get("Misc>Rainbow Mode>Enabled", default=False))

    def _read_rainbow_cycle_duration(self) -> int:
        value = config.get("Misc>Rainbow Mode>Cycle Duration", default=5000)
        if isinstance(value, bool):
            return 5000
        if not isinstance(value, (int, float, str)):
            return 5000
        try:
            return max(1000, int(value))
        except (TypeError, ValueError):
            return 5000

    def _sync_rainbow_settings_state(self) -> None:
        enabled = self._is_rainbow_mode_enabled()
        self._rainbow_cycle_duration_setting.setEnabled(enabled)
        self._rainbow_palette_setting.setEnabled(enabled)

    def _apply_runtime_theme_preferences(self) -> None:
        window = self.window()
        reapply = getattr(window, "reapply_runtime_theme_preferences", None)
        if callable(reapply):
            reapply()

    def _on_rainbow_mode_toggled(self, checked: bool) -> None:
        self._sync_rainbow_settings_state()
        self._apply_runtime_theme_preferences()

    def _commit_rainbow_cycle_duration_change(self) -> None:
        current = self._read_rainbow_cycle_duration()
        if current == self._last_applied_rainbow_cycle_duration:
            return
        self._last_applied_rainbow_cycle_duration = current
        if self._is_rainbow_mode_enabled():
            self._apply_runtime_theme_preferences()

    def _on_rainbow_palette_changed(self, _value: str) -> None:
        if self._is_rainbow_mode_enabled():
            self._apply_runtime_theme_preferences()
