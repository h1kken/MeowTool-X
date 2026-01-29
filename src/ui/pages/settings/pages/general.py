from PySide6.QtWidgets import QWidget
from src.ui.widgets import (
    ColumnsSetting, CollapsibleContainer
)
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets.settings_widgets import CheckboxSetting, SliderSetting
from src.config.loader import config_loader
from src.config.manager import config


class SettingsGeneralPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            CollapsibleContainer(
                tr_key='UPDTS',
                obj_name='Updates_Settings',
                widgets=[
                    CheckboxSetting(
                        config=config_loader,
                        tr_key='CHCK_UPDTS',
                        cfg_key='Updater>Check Updates',
                        default=True,
                    ),
                    CheckboxSetting(
                        config=config_loader,
                        tr_key='SV_OLD_VRSNS',
                        cfg_key='Updater>Save Old Versions',
                        default=True,
                    ),
                    SliderSetting(
                        config=config,
                        tr_key='THRDS',
                        cfg_key='Roblox>Cookie Checker>Threads',
                        min_value=1,
                        max_value=1000,
                        default=20,
                    )
                ]
            )
        ]

        columns_widget = ColumnsSetting(tabs, 2)
        main_layout.addWidget(columns_widget)
