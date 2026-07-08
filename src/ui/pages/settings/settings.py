from __future__ import annotations

from PySide6.QtCore import Signal, SignalInstance
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.translation.manager import TranslationManager
from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages.settings.pages import (
    SettingsMainPage,
    SettingsOutputsPage,
    SettingsProxyPage,
    SettingsRobloxPage,
    SettingsMiscPage,
    SettingsConfigPage,
    SettingsThemePage,
)
from src.ui.widgets import MTButton, MTWidget


class SettingsPage(MTWidget):
    presence_path_changed = Signal(str)

    _PAGES: list[tuple[str, str, type[QWidget]]] = [
        ("Main", "MAIN", SettingsMainPage),
        ("Outputs", "OUTPUTS", SettingsOutputsPage),
        ("Proxy", "PROXY", SettingsProxyPage),
        ("Roblox", "ROBLOX", SettingsRobloxPage),
        ("Misc", "MISC", SettingsMiscPage),
        ("Config", "CONFIG", SettingsConfigPage),
        ("Theme", "THEME", SettingsThemePage),
    ]

    def __init__(
        self,
        *,
        config: Config,
        translator: TranslationManager,
        current_theme_name: str | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._config_loader: ConfigLoader = config.loader
        self._translator = translator
        self._tab_names_by_key: dict[str, str] = {}
        self._pages_by_key: dict[str, QWidget] = {}
        self._current_theme_name = current_theme_name

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name="Settings_Main_Tabs_Widget")
        main_layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, parent=main_widget)

        self._page_controller = PageController(main_layout)

        for obj_name, tr_key, PageClass in self._PAGES:
            self._tab_names_by_key[tr_key] = obj_name
            page = self._create_page(PageClass)
            self._pages_by_key[tr_key] = page
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            if isinstance(page, (SettingsProxyPage, SettingsRobloxPage)):
                presence_signal: SignalInstance = page.presence_path_changed
                def _forward_presence_path(*_args: object) -> None:
                    self._emit_presence_path()

                presence_signal.connect(_forward_presence_path)
            self._page_controller.add_page(
                tr_key, page, obj_name=f"Settings_{obj_name}_Page"
            )

            btn = MTButton(tr_key=tr_key, obj_name=f"Settings_{obj_name}_Tab_Button")
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)

        tabs_layout.addStretch()
        self._page_controller.show(self._PAGES[0][1])  # show the first page
        self._page_controller.on_change(lambda _key: self._emit_presence_path())
        self._emit_presence_path()

    def _create_page(self, page_class: type[QWidget]) -> QWidget:
        if page_class is SettingsMainPage:
            return page_class(config=self._config, translator=self._translator)
        if page_class is SettingsOutputsPage:
            return page_class(config=self._config)
        if page_class is SettingsProxyPage:
            return page_class(config=self._config)
        if page_class is SettingsRobloxPage:
            return page_class(config=self._config)
        if page_class is SettingsMiscPage:
            return page_class(
                config_loader=self._config_loader,
                config=self._config,
            )
        if page_class is SettingsConfigPage:
            return page_class(
                config_loader=self._config_loader,
                config=self._config,
            )
        if page_class is SettingsThemePage:
            return page_class(
                config_loader=self._config_loader,
                config=self._config,
                autoload_name=self._current_theme_name,
            )
        return page_class()

    def current_presence_path(self) -> str:
        top_key = self._page_controller.current_key()
        if not isinstance(top_key, str):
            return "Settings"

        top_label = self._tab_names_by_key.get(top_key, top_key)
        page = self._pages_by_key.get(top_key)
        if isinstance(page, (SettingsProxyPage, SettingsRobloxPage)):
            subpage = str(page.current_presence_subpage()).strip()
            if subpage and subpage != top_label:
                return f"Settings: {top_label} > {subpage}"
        return f"Settings: {top_label}"

    def _emit_presence_path(self) -> None:
        self.presence_path_changed.emit(self.current_presence_path())
