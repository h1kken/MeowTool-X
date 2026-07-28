from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QMainWindow

from src.app.paths import PATH_SIDEBAR_ICONS_SRC
from src.ui.constants import MAIN_WINDOW_PAGE_LABEL_FALLBACK, WINDOW_X, WINDOW_Y
from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages import (
    ProxyCheckerPage,
    RobloxCookieCheckerPage,
    RobloxCookieRefresherPage,
    RobloxCookieSorterPage,
    SettingsPage,
)
from src.ui.types import PageState
from src.ui.widgets import (
    MTButton,
    MTWidget,
    MTSidebarButton,
    SidebarMediaWidget,
)
from src.ui.windows.types import PageSpec
from src.ui.windows.window_header import MTWindowHeader

if t.TYPE_CHECKING:
    from src.config.manager import Config

_PAGES: list[PageSpec | None] = [
    ("checker.svg", "Proxy_Checker", "CHCKR", ProxyCheckerPage),
    ("sorter.svg", "Roblox_Cookie_Sorter", "CK_SRTR", RobloxCookieSorterPage),
    ("checker.svg", "Roblox_Cookie_Checker", "CK_CHCKR", RobloxCookieCheckerPage),
    ("refresher.svg", "Roblox_Cookie_Refresher", "CK_RFRSHR", RobloxCookieRefresherPage),
    None,
    ("settings.svg", "Settings", "STNGS", SettingsPage),
]


class MainWindow(QMainWindow):
    page_changed = Signal(dict)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        
        self._page_state: PageState = {"main": "Startup"}
        
        self._build(config)

    def _build(self, config: Config) -> None:
        self.setObjectName("Main_Window")
        self.resize(WINDOW_X, WINDOW_Y)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        central_widget = MTWidget(obj_name="Central_Widget")
        self.setCentralWidget(central_widget)
        central_layout = create_layout(LayoutType.VBOX, parent=central_widget)
        
        header_widget = MTWindowHeader(self)

        body_widget = MTWidget(obj_name="Window_Body_Widget")
        body_layout = create_layout(LayoutType.HBOX, parent=body_widget)
        
        sidebar_widget = MTWidget(obj_name="Sidebar_Widget")
        sidebar_layout = create_layout(LayoutType.VBOX, parent=sidebar_widget)
        sidebar_layout.addWidget(SidebarMediaWidget(sidebar_widget))
        
        main_content = MTWidget(obj_name="Main_Content_Widget")
        pages_layout = create_layout(LayoutType.VBOX, parent=main_content)
        
        central_layout.addWidget(header_widget)
        central_layout.addWidget(body_widget, stretch=1)
        body_layout.addWidget(sidebar_widget)
        body_layout.addWidget(main_content)

        self._page_controller = PageController(pages_layout)

        first_page: tuple[str, str] | None = None

        for page_spec in _PAGES:
            if page_spec is None:
                sidebar_layout.addStretch()
                continue

            icon_name, obj_name, page_key, page_class = page_spec
            if page_class is SettingsPage:
                page: MTWidget = SettingsPage(config=config)
                page.page_changed.connect(self._on_settings_page_changed)
            elif page_class is RobloxCookieSorterPage:
                page = RobloxCookieSorterPage(config=config)
            else:
                page = page_class()

            page_label = obj_name.replace("_", " ")
            self._page_controller.add_page(page_key, page, obj_name=f"Main_{obj_name}_Page")

            button = MTSidebarButton(tr_key=page_key, obj_name=f"Sidebar_{obj_name}_Button")
            self._apply_sidebar_icon(button, icon_name)
            self._page_controller.bind_tab(page_key, button)

            if isinstance(page, SettingsPage):
                button.clicked.connect(lambda _checked=False, settings=page: self._set_page_state(settings.current_page()))
            else:
                button.clicked.connect(lambda _checked=False, label=page_label: self._set_page_state({"main": label}))

            sidebar_layout.addWidget(button)

            if first_page is None:
                first_page = (page_key, page_label)

        if first_page is not None:
            page_key, page_label = first_page
            self._page_controller.show(page_key)
            self._set_page_state({"main": page_label})

    @classmethod
    def _apply_sidebar_icon(cls, button: MTButton, icon_name: str | None) -> None:
        if icon_name is None:
            return

        icon_path = PATH_SIDEBAR_ICONS_SRC / icon_name
        if not icon_path.is_file():
            return

        button.set_text_icon(
            source=str(icon_path),
            align="left",
            size=QSize(16, 16),
            spacing=3.0,
        )

    def _set_page_state(self, state: PageState) -> None:
        normalized: PageState = {"main": state.get("main", "") or MAIN_WINDOW_PAGE_LABEL_FALLBACK}
        inner = state.get("inner")
        if isinstance(inner, tuple):
            normalized_inner = tuple(
                value
                for value in (str(part).strip() for part in inner)
                if value
            )
            if normalized_inner:
                normalized["inner"] = normalized_inner

        if normalized == self._page_state:
            return

        self._page_state = normalized
        self.page_changed.emit(normalized)

    def _on_settings_page_changed(self, state: PageState) -> None:
        if self._page_controller.current_key() == "STNGS":
            self._set_page_state(state)

    def current_state(self) -> PageState:
        return self._page_state.copy()
