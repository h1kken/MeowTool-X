import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QSize, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QMoveEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import QBoxLayout, QMainWindow, QSizePolicy, QWidget

from src.app.paths import (
    PATH_APP_ICON,
    PATH_DEFAULT_THEME,
    PATH_SIDEBAR_ICONS_SRC,
    PATH_THEMES_USER,
)
from src.ui.widgets import SidebarButton, SidebarCategory
from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.theme.animation.manager import AnimationManager
from src.theme.constants import (
    THEME_AUTOLOAD_FALLBACK,
    THEME_RUNTIME_RAINBOW_DURATION_FALLBACK,
    THEME_RUNTIME_RAINBOW_ENABLED_FALLBACK,
    THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK,
)
from src.theme.manager import ThemeManager
from src.theme.rainbow.runtime import RainbowRuntimeController
from src.theme.storage.io import (
    find_theme_file_by_name,
    load_theme_payload,
    theme_output_path,
    write_theme_payload,
)
from src.theme.storage.loader import resolve_theme_path
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
    THEME_AUTO_SAVE_DEBOUNCE_MS,
    WINDOW_X,
    WINDOW_Y,
)
from src.ui.widgets import MTButton, MTWidget, SidebarMediaWidget
from src.ui.windows.types import PageSpec, SidebarSectionSpec
from src.ui.windows.window_header import apply_frameless_window_header
from src.app.constants import PROGRAM_NAME
from src.utils.filesystem import FS
from src.translation.manager import TranslationManager


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

    def __init__(
        self,
        *,
        config_loader: ConfigLoader,
        config: Config,
        translator: TranslationManager,
    ) -> None:
        super().__init__()
        self._config_loader = config_loader
        self._config = config
        self._translator = translator
        self._theme_auto_save_timer = QTimer(self)
        self._theme_auto_save_timer.setSingleShot(True)
        self._theme_auto_save_timer.setInterval(THEME_AUTO_SAVE_DEBOUNCE_MS)
        self._theme_auto_save_timer.timeout.connect(self.auto_save_current_theme_if_enabled)

        self._window_move_idle_timer = QTimer(self)
        self._window_move_idle_timer.setSingleShot(True)
        self._window_move_idle_timer.setInterval(160)
        self._window_move_idle_timer.timeout.connect(self._on_window_move_idle)

        self._deferred_theme_auto_save = False
        self._settings_page: SettingsPage | None = None
        self._animation_manager: AnimationManager | None = None
        self._rainbow_runtime: RainbowRuntimeController | None = None
        self._theme_manager: ThemeManager | None = None
        self._presence_page = "Startup"
        self._settings_presence_label = "Settings"

        self._current_theme_name = ""

        self._sidebar_widget: MTWidget | None = None
        self._sidebar_media: SidebarMediaWidget | None = None
        self._sidebar_buttons: list[SidebarButton] = []
        self._sidebar_categories: list[SidebarCategory] = []
        self._sidebar_width_locked = False

        self._runtime_theme_preferences_cache: tuple[bool, int, str] | None = None
        self._runtime_theme_post_show_pending = True
        self._pages_built = False

        self._initial_theme_name = self.theme_on_load_name()

        self.setObjectName("Main_Window")
        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(str(PATH_APP_ICON)))
        self.resize(WINDOW_X, WINDOW_Y)

        self._build_window_shell()

        self._config.config_loaded.connect(self._on_config_loaded)
        self._config.value_changed.connect(self._on_config_value_changed)

        FS.ensure_dir(PATH_THEMES_USER)

    def resolve_theme_path(self, theme_name: str) -> Path | None:
        return resolve_theme_path(theme_name)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._window_move_idle_timer.start()
        self._defer_theme_related_activity_for_window_motion()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.repaint()
        self.centralWidget().repaint()

    def _defer_theme_related_activity_for_window_motion(self) -> None:
        if self._theme_auto_save_timer.isActive():
            self._theme_auto_save_timer.stop()
            self._deferred_theme_auto_save = True

    def _on_window_move_idle(self) -> None:
        if self._deferred_theme_auto_save and self._config_loader.auto_save_theme:
            self._deferred_theme_auto_save = False
            self._theme_auto_save_timer.start()
            return
        self._deferred_theme_auto_save = False

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._runtime_theme_post_show_pending:
            return
        self._runtime_theme_post_show_pending = False
        QTimer.singleShot(0, self.reapply_runtime_theme_preferences)
        QTimer.singleShot(32, self.reapply_runtime_theme_preferences)

    def _create_main_page(
        self,
        obj_name: str,
        tr_key: str,
        page_class: type[QWidget],
    ) -> QWidget:
        if tr_key == "STNGS":
            page = SettingsPage(
                config_loader=self._config_loader,
                config=self._config,
                translator=self._translator,
                current_theme_name=self._initial_theme_name,
            )
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

    def initialize_runtime_controllers(self) -> None:
        self.init_runtime_controllers()

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

    def init_runtime_controllers(self) -> None:
        if self._animation_manager is None:
            self._animation_manager = AnimationManager(self.centralWidget())

        if self._rainbow_runtime is None:
            self._rainbow_runtime = RainbowRuntimeController(self.centralWidget())

        self._rainbow_runtime.bind_animation_manager(self._animation_manager)

    def initialize_theme_manager(
        self,
        *,
        default_payload: dict[str, Any] | None = None,
    ) -> None:
        if self._theme_manager is not None:
            return

        payload = (
            deepcopy(default_payload)
            if isinstance(default_payload, dict)
            else self._load_default_theme_payload()
        )
        self._theme_manager = ThemeManager(self, payload)
        self._theme_manager.suppress_theme_changed()

    def apply_startup_theme(self, theme_name: str | None = None) -> str:
        target_theme = str(theme_name or self._initial_theme_name).strip() or PATH_DEFAULT_THEME.stem
        if not self.set_theme(target_theme, persist=False):
            self.set_theme(PATH_DEFAULT_THEME.stem, persist=False)
        self._lock_sidebar_width_once()
        return self.current_theme_name()

    @property
    def theme_manager(self) -> ThemeManager:
        if self._theme_manager is None:
            raise RuntimeError("Theme manager is not initialized.")
        return self._theme_manager

    def resume_theme_events(self) -> None:
        if self._theme_manager is None:
            return
        self._theme_manager.resume_theme_changed(flush=True)

    def current_presence_page(self) -> str:
        return self._presence_page

    def current_theme_name(self) -> str:
        current = str(self._current_theme_name).strip()
        if current:
            return current
        initial = str(self._initial_theme_name).strip()
        return initial or PATH_DEFAULT_THEME.stem

    def theme_on_load_name(self) -> str:
        if not bool(
            self._config.get(
                "Theme>Autoload Selected Theme",
                default=THEME_AUTOLOAD_FALLBACK,
            )
        ):
            return PATH_DEFAULT_THEME.stem
        configured = str(
            self._config.get("General>Theme", default=PATH_DEFAULT_THEME.stem)
        ).strip()
        return configured or PATH_DEFAULT_THEME.stem

    def _on_config_loaded(self) -> None:
        self._invalidate_runtime_theme_preferences_cache()
        self.reapply_runtime_theme_preferences()

    def _on_config_value_changed(self, key: str, _value: object) -> None:
        normalized = str(key).strip().replace(" ", "")
        if normalized in {
            "Misc>RainbowMode>Enabled",
            "Misc>RainbowMode>CycleDuration",
            "Misc>RainbowMode>Palette",
        }:
            self._invalidate_runtime_theme_preferences_cache()
            self.reapply_runtime_theme_preferences()

    def set_theme(self, theme_name: str, *, persist: bool = True) -> bool:
        if self._theme_manager is None:
            return False
        theme_path = self.resolve_theme_path(theme_name)
        if theme_path is None:
            return False

        self._theme_manager.load(theme_path, merge_with_default=False)
        self._current_theme_name = theme_path.stem
        self.reapply_loaded_theme()

        if persist:
            current = str(self._config.get("General>Theme", default=""))
            if current != theme_path.stem:
                self._config.set("General>Theme", theme_path.stem)

        return True

    def reapply_loaded_theme(self) -> None:
        if self._theme_manager is None:
            return
        self._theme_manager.apply()
        self._reload_main_animations_from_theme()
        self.reapply_runtime_theme_preferences()
        self.update()
        central = self.centralWidget()
        central.update()
        central.updateGeometry()

    def save_current_theme_as(self, theme_name: str) -> Path | None:
        if self._theme_manager is None:
            return None

        name = Path(str(theme_name).strip()).stem.strip()
        if not name or name.startswith("."):
            return None

        payload = self._theme_payload_for_save()

        output_path = find_theme_file_by_name(
            PATH_THEMES_USER, name
        ) or theme_output_path(PATH_THEMES_USER, name)
        FS.ensure_dir(PATH_THEMES_USER)
        try:
            write_theme_payload(output_path, payload)
        except OSError:
            return None

        return output_path

    def _theme_payload_for_save(self) -> dict[str, Any]:
        current_theme = deepcopy(self._build_theme_payload_from_manager())
        widgets = current_theme.get("widgets")
        if isinstance(widgets, list):
            return current_theme

        widgets_payload = self._widgets_dict_to_payload(cast(dict[str, dict[str, Any]], widgets if isinstance(widgets, dict) else {}))
        payload: dict[str, Any] = {
            key: deepcopy(value)
            for key, value in current_theme.items()
            if key != "widgets"
        }
        payload["widgets"] = widgets_payload
        return payload

    def _load_default_theme_payload(self) -> dict[str, Any]:
        return load_theme_payload(PATH_DEFAULT_THEME)

    def _widgets_dict_to_payload(
        self, widgets: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []

        for target, data in widgets.items():
            if not target:
                continue

            styles = {
                key: deepcopy(value)
                for key, value in data.items()
                if key != "animations"
            }

            animations_present = "animations" in data
            animations_payload: Any = None
            if "animations" in data:
                animations_payload = deepcopy(data.get("animations"))

            if not styles and not animations_present:
                continue

            grouping_key = json.dumps(
                {
                    "styles": styles if styles else None,
                    "animations": animations_payload if animations_present else None,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if target == "*":
                grouping_key = f"__global__::{target}"

            if grouping_key not in grouped:
                entry: dict[str, Any] = {"targets": [target]}
                if styles:
                    entry["styles"] = styles
                if animations_present:
                    entry["animations"] = animations_payload
                grouped[grouping_key] = entry
                order.append(grouping_key)
                continue

            grouped[grouping_key]["targets"].append(target)

        return [grouped[key] for key in order]

    def request_auto_save_current_theme_if_enabled(self) -> None:
        if not self._config_loader.auto_save_theme:
            return

        if self._window_move_idle_timer.isActive():
            self._deferred_theme_auto_save = True
            return

        self._theme_auto_save_timer.start()

    def auto_save_current_theme_if_enabled(self) -> Path | None:
        if not self._config_loader.auto_save_theme:
            return None

        return self.save_current_theme_as(self.current_theme_name())

    def _reload_main_animations_from_theme(self) -> None:
        if self._theme_manager is None or self._animation_manager is None:
            return

        widgets = self._theme_manager.current_theme_widgets()
        animations: dict[str, Any] = {}
        for target, item in widgets.items():
            animation_data = item.get("animations")
            if animation_data is not None:
                animations[target] = deepcopy(animation_data)
        self._animation_manager.load(animations, widgets)

    def _apply_runtime_theme_preferences_for_controller(
        self,
        controller: RainbowRuntimeController | None,
        preferences: tuple[bool, int, str] | None = None,
    ) -> None:
        if controller is None:
            return
        enabled, duration, palette = preferences or self._runtime_theme_preferences()
        controller.set_enabled(enabled, duration, palette=palette)

    def _apply_runtime_theme_preferences_to_children(self) -> None:
        preferences = self._runtime_theme_preferences()
        enabled, duration, palette = preferences
        self._window_header.set_title_rainbow(enabled, duration, palette=palette)

        self._apply_runtime_theme_preferences_for_controller(self._rainbow_runtime, preferences)

    def _build_theme_payload_from_manager(self) -> dict[str, Any]:
        if self._theme_manager is None:
            return {"widgets": []}

        current_theme = self._theme_manager.current_theme
        widgets = self._theme_manager.current_theme_widgets()
        payload = {
            key: deepcopy(value)
            for key, value in current_theme.items()
            if key != "widgets"
        }
        payload["widgets"] = self._widgets_dict_to_payload(widgets)
        return payload

    def _payload_widgets_dict(
        self, payload: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        parser = ThemeManager(self, emit_theme_changed=False)
        parser.load(payload, merge_with_default=False)
        return parser.current_theme_widgets()

    def _runtime_theme_preferences(self) -> tuple[bool, int, str]:
        if self._runtime_theme_preferences_cache is not None:
            return self._runtime_theme_preferences_cache

        enabled = bool(
            self._config.get(
                "Misc>Rainbow Mode>Enabled",
                default=THEME_RUNTIME_RAINBOW_ENABLED_FALLBACK,
            )
        )
        try:
            duration = max(
                1000,
                int(str(self._config.get(
                    "Misc>Rainbow Mode>Cycle Duration",
                    default=THEME_RUNTIME_RAINBOW_DURATION_FALLBACK,
                ))),
            )
        except (TypeError, ValueError):
            duration = THEME_RUNTIME_RAINBOW_DURATION_FALLBACK

        palette = (
            str(
                self._config.get(
                    "Misc>Rainbow Mode>Palette",
                    default=THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK,
                )
            ).strip()
            or THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK
        )
        self._runtime_theme_preferences_cache = (enabled, duration, palette)
        return self._runtime_theme_preferences_cache

    def _invalidate_runtime_theme_preferences_cache(self) -> None:
        self._runtime_theme_preferences_cache = None

    def _effective_theme_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(payload)

    def reapply_runtime_theme_preferences(self) -> None:
        self._apply_runtime_theme_preferences_to_children()
