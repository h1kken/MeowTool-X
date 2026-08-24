from __future__ import annotations

import typing as t

from PySide6.QtWidgets import QWidget

import src.app.context as ctx
from src.app.paths import PATH_TRANSLATIONS_SRC, PATH_TRANSLATIONS_USER
from src.translation import Translation as Tr
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTCollapsibleContainer
from src.ui.widgets.settings import MTColumnsSetting, MTComboBoxSetting
from src.ui.widgets.types import ComboItem

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsMainPage(BasePage):
    _OBJECT_NAME = 'Main'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsMainPage._OBJECT_NAME))

        self._build_ui()

    def _build_ui(self)-> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._columns_widget = MTColumnsSetting(obj_name=(obj_name,), tabs=self._create_settings())
        self._main_layout.addWidget(self._columns_widget)

    def _create_settings(self) -> list[MTCollapsibleContainer]:
        obj_name = self.objectName()
        return [
            MTCollapsibleContainer(
                tr=Tr(key='GNRL'),
                obj_name=(obj_name, 'General'),
                widgets=[
                    MTComboBoxSetting(
                        config=self._config,
                        cfg_key='General>Language',
                        tr=Tr(key='LANG'),
                        obj_name=(obj_name, 'Language'),
                        items=self._get_all_languages(),
                        on_changed=ctx.services.translator.load,
                    ),
                ],
            ),
        ]

    def _get_all_languages(self) -> list[ComboItem]:
        languages: set[ComboItem] = set()

        for translations_path in (PATH_TRANSLATIONS_USER, PATH_TRANSLATIONS_SRC):
            if not translations_path.is_dir():
                continue

            for path in translations_path.glob('*.axis'):
                languages.add(ComboItem(Tr(key=path.stem), path.stem))
        
        return sorted(languages, key=lambda item: item.tr.key.lower())
