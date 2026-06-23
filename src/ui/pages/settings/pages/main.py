from src.config.manager import config
from src.translation.manager import translator
from src.translation.constants import SYSTEM_LOCALE
from src.translation.paths import PATH_TRANSLATIONS_SOURCE, PATH_TRANSLATIONS_USER
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTComboBoxSetting,
    MTWidget,
)


class SettingsMainPage(MTWidget):
    def __init__(self):
        super().__init__()
        main_layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_General_Settings",
                widgets=[
                    MTComboBoxSetting(
                        config=config,
                        tr_key="LANG",
                        cfg_key="General>Language",
                        items=self._get_all_languages(),
                        default=SYSTEM_LOCALE,
                        on_changed=self._on_language_changed,
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs, 2, obj_name="Settings_General_Columns")
        main_layout.addWidget(columns_widget)
        config.config_loaded.connect(self._apply_runtime_settings)

    def _get_all_languages(self) -> list[tuple[str, str]]:
        return self._merge_languages(
            *(
                path.stem
                    for path in PATH_TRANSLATIONS_SOURCE.glob("*.axis")
                        if path.is_file()
            ),
            *(
                path.stem
                    for path in PATH_TRANSLATIONS_USER.glob("*.axis")
                        if path.is_file()
            ),
        )

    @staticmethod
    def _language_display_name(value: str) -> str:
        normalized = str(value).strip().replace("-", "_")
        family = normalized.split("_", 1)[0].lower()
        match family:
            case "en":
                return "English"
            case "ru":
                return "Русский"
            case _:
                return normalized

    @classmethod
    def _merge_languages(cls, *values: str) -> list[tuple[str, str]]:
        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for value in values:
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            result.append((cls._language_display_name(value), value))
        return result

    def _on_language_changed(self, language_name: str) -> None:
        translator.load_language(str(language_name).strip())

    def _apply_runtime_settings(self) -> None:
        self._on_language_changed(
            str(config.get("General>Language", default=SYSTEM_LOCALE))
        )
