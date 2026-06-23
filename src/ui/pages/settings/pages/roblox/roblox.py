from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages.settings.pages.roblox import (
    SettingsRobloxCookieSorterPage,
    SettingsRobloxCookieCheckerPage,
    SettingsRobloxCookieRefresherPage,
    # SettingsRobloxTimeBoosterPage,
)
from src.ui.widgets import MTButton, MTWidget


class SettingsRobloxPage(MTWidget):
    presence_path_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._tab_labels_by_key: dict[str, str] = {}

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name="Settings_Roblox_Tabs_Widget")
        main_layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, parent=main_widget)

        self._page_controller = PageController(main_layout)

        PAGES: list[tuple[str, str, type[QWidget] | None]] = [
            ("Cookie_Sorter", "C_SRTR", SettingsRobloxCookieSorterPage),
            ("Cookie_Checker", "C_CHCKR", SettingsRobloxCookieCheckerPage),
            ("Cookie_Refresher", "C_RFRSHR", SettingsRobloxCookieRefresherPage),
            # ('Time_Booster',     'TM_BSTR',  SettingsRobloxTimeBoosterPage),
            ("", "", None),
        ]

        first_key: str | None = None

        for obj_name, tr_key, PageClass in PAGES:
            if PageClass is None:
                tabs_layout.addStretch()
                continue

            self._tab_labels_by_key[tr_key] = str(obj_name).replace("_", " ")

            page = PageClass()
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._page_controller.add_page(
                tr_key, page, object_name=f"Settings_Roblox_{obj_name}_Page"
            )

            btn = MTButton(
                tr_key=tr_key, obj_name=f"Settings_Roblox_{obj_name}_Tab_Button"
            )
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)

            if first_key is None:
                first_key = tr_key
                self._page_controller.show(first_key)

        self._page_controller.on_change(lambda _key: self._emit_presence_path())

    def current_presence_subpage(self) -> str:
        key = self._page_controller.current_key()
        if not isinstance(key, str):
            return "Roblox"
        return self._tab_labels_by_key.get(key, key)

    def _emit_presence_path(self) -> None:
        self.presence_path_changed.emit(self.current_presence_subpage())
