from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

from src.app.paths import PATH_DEFAULT_TRANSLATION, PATH_TRANSLATIONS_SRC, PATH_TRANSLATIONS_USER
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTComboBoxSetting

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsMainPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(parent, config=config, obj_name=obj_name)

        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._settings = [
            MTCollapsibleContainer(
                tr_key='GNRL',
                obj_name='Settings_General_Settings',
                widgets=[
                    MTComboBoxSetting(
                        config=self._config,
                        cfg_key='General>Language',
                        tr_key='LANG',
                        items=self._get_all_languages(),
                        default=PATH_DEFAULT_TRANSLATION.stem,
                        on_changed=self._reload_language,
                    ),
                ],
            ),
        ]

        self._columns_widget = MTColumnsSetting(obj_name='Settings_General_Columns', tabs=self._settings)
        self._main_layout.addWidget(self._columns_widget)

    def _get_all_languages(self) -> list[str]:
        languages = {PATH_DEFAULT_TRANSLATION.stem}

        for base_path in (PATH_TRANSLATIONS_USER, PATH_TRANSLATIONS_SRC):
            if not base_path.is_dir():
                continue

            for path in base_path.glob('*.axis'):
                languages.add(path.stem)

        return sorted(languages, key=str.lower)

    def _reload_language(self, name: str) -> None:
        import src.app.context as ctx

        ctx.services.translator.load(name)
