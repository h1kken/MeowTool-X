from __future__ import annotations

from src.app.paths import PATH_DEFAULT_TRANSLATION
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTComboBoxSetting,
    MTWidget,
)


class SettingsMainPage(MTWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_General_Settings",
                widgets=[
                    MTComboBoxSetting(
                        tr_key="LANG",
                        cfg_key="General>Language",
                        items=self._get_all_languages(),
                        default=PATH_DEFAULT_TRANSLATION.stem,
                        on_changed=self._on_language_changed,
                    ),
                ],
            ),
        ]

        columns = MTColumnsSetting(tabs, obj_name="Settings_General_Columns")
        self._layout.addWidget(columns)
