from typing import Callable

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QSizePolicy, QWidget

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

    PAGE_SPECS: list[tuple[str, str, type[QWidget]]] = [
        ("Main", "MAIN", SettingsMainPage),
        ("Outputs", "OUTPUTS", SettingsOutputsPage),
        ("Proxy", "PROXY", SettingsProxyPage),
        ("Roblox", "ROBLOX", SettingsRobloxPage),
        ("Misc", "MISC", SettingsMiscPage),
        ("Config", "CONFIG", SettingsConfigPage),
        ("Theme", "THEME", SettingsThemePage),
    ]
    HEAVY_TAB_KEYS: tuple[str, ...] = ("CONFIG", "THEME")

    def __init__(
        self,
        *,
        startup_progress: Callable[[int, int, str], None] | None = None,
        current_theme_name: str | None = None,
    ):
        super().__init__()
        self._heavy_tabs_preloaded = False
        self._heavy_tab_keys: list[str] = []
        self._tab_names_by_key: dict[str, str] = {}
        self._pages_by_key: dict[str, QWidget] = {}
        self._startup_progress = startup_progress
        self._current_theme_name = current_theme_name

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name="Settings_Main_Tabs_Widget")
        main_layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, parent=main_widget)

        self._page_controller = PageController(main_layout)

        first_key: str | None = None
        total_pages = len(self.PAGE_SPECS)

        for index, (obj_name, tr_key, PageClass) in enumerate(self.PAGE_SPECS, start=1):
            self._tab_names_by_key[tr_key] = obj_name
            if PageClass is SettingsThemePage:
                page = PageClass(autoload_name=self._current_theme_name)
            else:
                page = PageClass()
            self._pages_by_key[tr_key] = page
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            presence_signal = getattr(page, "presence_path_changed", None)
            if presence_signal is not None:
                presence_signal.connect(lambda *_args: self._emit_presence_path())
            self._page_controller.add_page(
                tr_key, page, object_name=f"Settings_{obj_name}_Page"
            )

            btn = MTButton(tr_key=tr_key, obj_name=f"Settings_{obj_name}_Tab_Button")
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)

            if tr_key in self.HEAVY_TAB_KEYS:
                self._heavy_tab_keys.append(tr_key)

            if callable(self._startup_progress):
                self._startup_progress(
                    index, total_pages, f"Loading settings: {obj_name}"
                )

            if first_key is None:
                first_key = tr_key

        tabs_layout.addStretch()
        self._page_controller.on_change(lambda _key: self._emit_presence_path())

        if first_key is not None:
            self._page_controller.show(first_key)
            self._emit_presence_path()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._heavy_tabs_preloaded:
            return
        self._heavy_tabs_preloaded = True
        QTimer.singleShot(0, self._preload_heavy_tabs)

    def preload_heavy_tabs(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        if self._heavy_tabs_preloaded:
            return
        self._heavy_tabs_preloaded = True
        self._preload_heavy_tabs(progress_callback=progress_callback)

    def _preload_heavy_tabs(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        def _relay_progress(current: int, total: int, key: str) -> None:
            if not callable(progress_callback):
                return

            tab_name = self._tab_names_by_key.get(key, key)
            progress_callback(current, total, f"Prewarming settings: {tab_name}")

        self._page_controller.preload(
            *self._heavy_tab_keys, progress_callback=_relay_progress
        )

    def current_presence_path(self) -> str:
        top_key = self._page_controller.current_key()
        if not isinstance(top_key, str):
            return "Settings"

        top_label = self._tab_names_by_key.get(top_key, top_key)
        page = self._pages_by_key.get(top_key)
        subpage_getter = getattr(page, "current_presence_subpage", None)
        if callable(subpage_getter):
            subpage = str(subpage_getter()).strip()
            if subpage and subpage != top_label:
                return f"Settings: {top_label} > {subpage}"
        return f"Settings: {top_label}"

    def _emit_presence_path(self) -> None:
        self.presence_path_changed.emit(self.current_presence_path())
