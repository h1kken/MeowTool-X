from __future__ import annotations

import typing as t

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy

from src.config.manager import Config
from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages.settings.pages.proxy import SettingsProxyCheckerPage
from src.ui.widgets import MTButton, MTWidget

ProxySettingsPageClass: t.TypeAlias = type[SettingsProxyCheckerPage]


class SettingsProxyPage(MTWidget):
    page_changed = Signal()

    _PAGES: list[tuple[str, str, ProxySettingsPageClass | None]] = [
        ("Checker", "CHCKR", SettingsProxyCheckerPage),
        ("", "", None),
    ]

    def __init__(self, *, config: Config) -> None:
        super().__init__()
        self._config = config
        self._tab_labels_by_key: dict[str, str] = {}

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name="Settings_Proxy_Tabs_Widget")
        main_layout.addWidget(main_widget)

        tabs_layout = create_layout(LayoutType.HBOX, parent=main_widget)

        self._page_controller = PageController(main_layout)

        for obj_name, tr_key, PageClass in self._PAGES:
            if PageClass is None:
                tabs_layout.addStretch()
                continue

            self._tab_labels_by_key[tr_key] = str(obj_name).replace("_", " ")

            page = PageClass(config=self._config)
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._page_controller.add_page(tr_key, page, obj_name=f"Settings_Proxy_{obj_name}_Page")

            btn = MTButton(tr_key=tr_key, obj_name=f"Settings_Proxy_{obj_name}_Tab_Button")
            self._page_controller.bind_tab(tr_key, btn)
            tabs_layout.addWidget(btn)
        
        self._page_controller.show(self._PAGES[0][1])  # show the first page
        self._page_controller.on_change(lambda _key: self._emit_page_changed())

    def current_page_inner(self) -> tuple[str, ...]:
        key = self._page_controller.current_key()
        if not isinstance(key, str):
            return ()

        label = self._tab_labels_by_key.get(key, key)
        return (label,) if label else ()

    def _emit_page_changed(self) -> None:
        self.page_changed.emit()
