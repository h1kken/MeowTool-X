from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QMainWindow, QSizePolicy, QWidget

from src.app.paths import (
    PATH_APP_ICON,
    PATH_SIDEBAR_ICONS_SRC,
)
from src.ui.widgets import SidebarButton, SidebarCategory
from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages import (
    ProxyCheckerPage,
    RobloxCookieSorterPage,
    RobloxCookieCheckerPage,
    RobloxCookieRefresherPage,
    # RobloxGameCheckerPage,
    # RobloxLogPassCheckerPage,
    # RobloxAutoReggerPage,
    # RobloxTimeBoosterPage,
    SettingsPage,
)
from src.ui.constants import (
    MAIN_WINDOW_PAGE_LABEL_FALLBACK,
    WINDOW_X,
    WINDOW_Y,
)
from src.ui.widgets import MTButton, MTWidget, SidebarMediaWidget
from src.ui.windows.types import PageSpec, SidebarSectionSpec
from src.ui.windows.window_header import apply_frameless_window_header
from src.app.constants import PROGRAM_NAME

if TYPE_CHECKING:
    from src.config.manager import Config


class MainWindow(QMainWindow):
    presence_page_changed = Signal(str)

    _PAGES: list[SidebarSectionSpec] = [
        (
            "PRX", "Sidebar_Proxy", [
                ("Proxy_Checker", "CHCKR", ProxyCheckerPage),
            ],
        ),
        (
            "RBX", "Sidebar_Roblox", [
                ("Roblox_Cookie_Sorter", "CK_SRTR", RobloxCookieSorterPage),
                ("Roblox_Cookie_Checker", "CK_CHCKR", RobloxCookieCheckerPage),
                ("Roblox_Cookie_Refresher", "CK_RFRSHR", RobloxCookieRefresherPage),
                # ('Roblox_Game_Checker', 'GM_CHCKR', RobloxGameCheckerPage),
                # ('Roblox_LogPass_Checker', 'LP_CHCKR', RobloxLogPassCheckerPage),
                # ('Roblox_Auto_Regger', 'AT_RGGR', RobloxAutoReggerPage),
                # ('Roblox_Time_Booster', 'TM_BSTR', RobloxTimeBoosterPage),
            ],
        ),
        ("", "", None),
        ("Settings", "STNGS", SettingsPage),
    ]
    _SIDEBAR_CATEGORY_ICON_NAMES: dict[str, str] = {
        "Sidebar_Proxy": "proxy.svg",
        "Sidebar_Roblox": "roblox.svg",
    }
    _SIDEBAR_ICON_NAMES: dict[str, str] = {
        "Proxy_Checker": "checker.svg",
        "Roblox_Cookie_Sorter": "sorter.svg",
        "Roblox_Cookie_Checker": "checker.svg",
        "Roblox_Cookie_Refresher": "refresher.svg",
        "Settings": "settings.svg",
    }

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        
        self._settings_page: SettingsPage | None = None
        self._presence_page = "Startup"
        self._settings_presence_label = "Settings"

        self._sidebar_widget: MTWidget | None = None
        self._sidebar_media: SidebarMediaWidget | None = None
        self._sidebar_buttons: list[SidebarButton] = []
        self._sidebar_categories: list[SidebarCategory] = []
        self._sidebar_width_locked = False

        self._pages_built = False

        self.setObjectName("Main_Window")
        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(str(PATH_APP_ICON)))
        self.resize(WINDOW_X, WINDOW_Y)

        self._build_window_shell()
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.repaint()
        self.centralWidget().repaint()

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)

    def _create_main_page(
        self,
        obj_name: str,
        tr_key: str,
        page_class: type[QWidget],
    ) -> QWidget:
        if tr_key == "STNGS":
            page = SettingsPage()
            self._settings_page = page
            page.presence_path_changed.connect(
                self._on_settings_presence_path_changed
            )
            return page

        if page_class is RobloxCookieSorterPage:
            return page_class(config=self._config)

        return page_class()

    def _register_page(
        self,
        obj_name: str,
        tr_key: str,
        page_class: type[QWidget],
    ) -> tuple[QWidget, str]:
        page_label = obj_name.replace("_", " ")
        page = self._create_main_page(obj_name, tr_key, page_class)
        self._page_controller.add_page(
            tr_key, page, obj_name=f"Main_{obj_name}_Page"
        )
        return page, page_label

    def _create_sidebar_button(
        self, obj_name: str, tr_key: str, page_label: str
    ) -> SidebarButton:
        button = SidebarButton(tr_key=tr_key, obj_name=f"Sidebar_{obj_name}_Button")
        self._apply_default_sidebar_button_icon(button, obj_name)
        self._page_controller.bind_tab(tr_key, button)
        button.clicked.connect(
            lambda _=False, label=page_label, key=tr_key: self._set_presence_page(
                self._settings_presence_label_text() if key == "STNGS" else label
            )
        )
        self._sidebar_buttons.append(button)
        return button

    @staticmethod
    def _pick_first_page(
        current_key: str | None,
        current_label: str | None,
        next_key: str,
        next_label: str,
    ) -> tuple[str | None, str | None]:
        if current_key is not None:
            return current_key, current_label
        return next_key, next_label

    def _build_standalone_sidebar_page(
        self,
        sidebar_layout: QBoxLayout,
        obj_name: str,
        tr_key: str,
        page_class: type[QWidget],
    ) -> tuple[str, str]:
        _page, page_label = self._register_page(obj_name, tr_key, page_class)
        button = self._create_sidebar_button(obj_name, tr_key, page_label)
        sidebar_layout.addWidget(button)
        return tr_key, page_label

    def _build_category_sidebar_pages(
        self,
        category_obj_name: str,
        page_specs: list[PageSpec],
        *,
        parent: QWidget,
        sidebar_layout: QBoxLayout,
    ) -> tuple[SidebarCategory, str | None, str | None]:
        category = SidebarCategory(
            obj_name=category_obj_name,
            parent=parent,
        )
        self._apply_default_sidebar_category_icon(category, category_obj_name)
        sidebar_layout.addWidget(category)
        self._sidebar_categories.append(category)

        first_key: str | None = None
        first_label: str | None = None

        for obj_name, tr_key, page_class in page_specs:
            _page, page_label = self._register_page(obj_name, tr_key, page_class)
            button = self._create_sidebar_button(obj_name, tr_key, page_label)
            category.add_button(button)
            first_key, first_label = self._pick_first_page(
                first_key, first_label, tr_key, page_label
            )

        return category, first_key, first_label

    def _build_window_shell(self) -> None:
        central_widget = MTWidget(obj_name="Central_Widget")
        self.setCentralWidget(central_widget)

        root_layout = create_layout(LayoutType.VBOX, parent=central_widget)
        self._window_header = apply_frameless_window_header(
            self,
            root_layout,
            allow_minimize=True,
            allow_maximize=True,
            obj_name="Main_Window_Header",
        )

        body_widget = MTWidget(obj_name="Window_Body_Widget")
        root_layout.addWidget(body_widget, stretch=1)
        self._popup_modal_host = body_widget

        main_layout = create_layout(LayoutType.HBOX, parent=body_widget)

        sidebar_widget = MTWidget(obj_name="Sidebar_Widget")
        sidebar_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self._sidebar_widget = sidebar_widget
        main_layout.addWidget(sidebar_widget)

        sidebar_buttons_layout = create_layout(LayoutType.VBOX, parent=sidebar_widget)
        self._sidebar_buttons_layout = sidebar_buttons_layout

        self._sidebar_media = SidebarMediaWidget(sidebar_widget)
        sidebar_buttons_layout.addWidget(self._sidebar_media)

        main_content = MTWidget(obj_name="Main_Content_Widget")
        main_layout.addWidget(main_content)

        pages_layout = create_layout(LayoutType.VBOX, parent=main_content)
        self._page_controller = PageController(pages_layout)

    def build_pages(self) -> None:
        if self._pages_built:
            return

        self._pages_built = True
        assert self._sidebar_widget is not None

        first_key: str | None = None
        first_page_label: str | None = None

        for category_name, category_obj_name, page_specs in self._PAGES:
            if page_specs is None:
                self._sidebar_buttons_layout.addStretch()
                continue

            if not isinstance(page_specs, list):
                next_key, next_label = self._build_standalone_sidebar_page(
                    self._sidebar_buttons_layout,
                    category_name,
                    category_obj_name,
                    page_specs,
                )
                first_key, first_page_label = self._pick_first_page(
                    first_key,
                    first_page_label,
                    next_key,
                    next_label,
                )
                continue

            _category, next_key, next_label = self._build_category_sidebar_pages(
                category_obj_name,
                page_specs,
                parent=self._sidebar_widget,
                sidebar_layout=self._sidebar_buttons_layout,
            )
            if next_key is not None and next_label is not None:
                first_key, first_page_label = self._pick_first_page(
                    first_key,
                    first_page_label,
                    next_key,
                    next_label,
                )

        if first_key is not None:
            self._page_controller.show(first_key)
            self._set_presence_page(
                first_page_label or MAIN_WINDOW_PAGE_LABEL_FALLBACK
            )

    def _apply_default_sidebar_button_icon(
        self, button: MTButton, obj_name: str
    ) -> None:
        icon_name = self._SIDEBAR_ICON_NAMES.get(obj_name)
        if not isinstance(icon_name, str) or not icon_name.strip():
            return

        icon_path = PATH_SIDEBAR_ICONS_SRC / icon_name.strip()
        if not icon_path.is_file():
            return

        button.set_text_icon(
            source=str(icon_path),
            align="left",
            size=QSize(16, 16),
            spacing=3.0,
        )

    def _apply_default_sidebar_category_icon(
        self,
        category: SidebarCategory,
        category_obj_name: str
    ) -> None:
        icon_name = self._SIDEBAR_CATEGORY_ICON_NAMES.get(category_obj_name)
        if not isinstance(icon_name, str) or not icon_name.strip():
            return

        icon_path = PATH_SIDEBAR_ICONS_SRC / icon_name.strip()
        if not icon_path.is_file():
            return

        category.header_button().set_text_icon(
            source=str(icon_path),
            align="top" if category.header_button().text() == "" else "left",
            size=QSize(14, 14),
            spacing=3.0,
        )

    def _lock_sidebar_width_once(self) -> None:
        if self._sidebar_width_locked:
            return
        if self._sidebar_widget is None:
            return

        self._sidebar_widget.ensurePolished()

        width_candidates: list[int] = []
        for category in self._sidebar_categories:
            category.ensurePolished()
            header_button = category.header_button()
            header_button.ensurePolished()
            width_candidates.append(header_button.sizeHint().width())

        for button in self._sidebar_buttons:
            button.ensurePolished()
            width_candidates.append(button.sizeHint().width())

        target_width = max(
            width_candidates, default=self._sidebar_widget.sizeHint().width()
        )
        if target_width <= 0:
            return

        target_width = max(target_width, self._sidebar_widget.minimumSizeHint().width())
        self._sidebar_widget.setFixedWidth(target_width)
        self._sidebar_width_locked = True

    def _set_presence_page(self, page_label: str) -> None:
        normalized = str(page_label).strip() or MAIN_WINDOW_PAGE_LABEL_FALLBACK
        if normalized == self._presence_page:
            return
        self._presence_page = normalized
        self.presence_page_changed.emit(normalized)

    def _settings_presence_label_text(self) -> str:
        if isinstance(self._settings_page, SettingsPage):
            label = str(self._settings_page.current_presence_path()).strip()
            if label:
                self._settings_presence_label = label
        return self._settings_presence_label or "Settings"

    def _on_settings_presence_path_changed(self, label: str) -> None:
        normalized = str(label).strip() or "Settings"
        self._settings_presence_label = normalized
        current_key = self._page_controller.current_key()
        if current_key == "STNGS":
            self._set_presence_page(normalized)

    def current_presence_page(self) -> str:
        return self._presence_page
