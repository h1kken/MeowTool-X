from __future__ import annotations

from src.app.paths import PATH_DEFAULT_TRANSLATION
from src.app.paths import PATH_TRANSLATIONS_SRC
from src.app.paths import PATH_TRANSLATIONS_USER
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
                        on_changed=self._reload_language,
                    ),
                ],
            ),
        ]

        columns = MTColumnsSetting(tabs, obj_name="Settings_General_Columns")
        self._layout.addWidget(columns)

    def _get_all_languages(self) -> list[str]:
        languages = {PATH_DEFAULT_TRANSLATION.stem}

        for base_path in (PATH_TRANSLATIONS_USER, PATH_TRANSLATIONS_SRC):
            if not base_path.is_dir():
                continue

            for path in base_path.glob("*.axis"):
                languages.add(path.stem)

        return sorted(languages, key=str.lower)

    def _reload_language(self, name: str) -> None:
        import src.app.context as ctx

        ctx.services.translator.load(name)
