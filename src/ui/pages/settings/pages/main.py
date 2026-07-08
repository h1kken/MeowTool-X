from __future__ import annotations

from pathlib import Path

import src.app.context as ctx
translator = ctx.services.translator
from src.app.paths import PATH_TRANSLATIONS_SRC, PATH_TRANSLATIONS_USER
from src.config.manager import Config
from src.translation.constants import DEFAULT_LANGUAGE
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTCollapsibleContainer,
    MTColumnsSetting,
    MTComboBoxSetting,
    MTWidget,
)


class SettingsMainPage(MTWidget):
    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config
        self._layout = create_layout(LayoutType.VBOX, parent=self)

        tabs = [
            MTCollapsibleContainer(
                tr_key="GNRL",
                obj_name="Settings_General_Settings",
                widgets=[
                    MTComboBoxSetting(
                        config=self._config,
                        tr_key="LANG",
                        cfg_key="General>Language",
                        items=translator.get_awailable_translations(),
                        default=DEFAULT_LANGUAGE,
                        on_changed=self._on_language_changed,
                    ),
                ],
            ),
        ]

        columns_widget = MTColumnsSetting(tabs, 2, obj_name="Settings_General_Columns")
        self._layout.addWidget(columns_widget)
        self._config.config_loaded.connect(self._apply_runtime_settings)

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

    @staticmethod
    def _resolve_translation_path(language_name: str) -> Path:
        normalized = Path(str(language_name).strip()).stem.strip().replace("-", "_")
        if not normalized:
            return PATH_TRANSLATIONS_SRC / f"{DEFAULT_LANGUAGE}.axis"

        for candidate in (
            PATH_TRANSLATIONS_USER / f"{normalized}.axis",
            PATH_TRANSLATIONS_SRC / f"{normalized}.axis",
        ):
            if candidate.is_file():
                return candidate

        return PATH_TRANSLATIONS_SRC / f"{DEFAULT_LANGUAGE}.axis"
