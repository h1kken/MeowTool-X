from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui.controllers import PageController
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.pages.settings.pages.proxy import SettingsProxyCheckerPage
from src.ui.widgets import MTButton, MTWidget


class SettingsProxyPage(MTWidget):
    presence_path_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._tab_labels_by_key: dict[str, str] = {}

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name="Settings_Proxy_Tabs_Widget")
        main_layout.addWidget(main_widget)

        tabs_hlayout = create_layout(LayoutType.HBOX, parent=main_widget)

        self._page_controller = PageController(main_layout)

        PAGES: list[tuple[str, str, type[QWidget] | None]] = [
            ("Checker", "CHCKR", SettingsProxyCheckerPage),
            ("", "", None),
        ]

        first_key: str | None = None

        for obj_name, tr_key, PageClass in PAGES:
            if PageClass is None:
                tabs_hlayout.addStretch()
                continue

            self._tab_labels_by_key[tr_key] = str(obj_name).replace("_", " ")

            page = PageClass()
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._page_controller.add_page(
                tr_key, page, object_name=f"Settings_Proxy_{obj_name}_Page"
            )

            btn = MTButton(
                tr_key=tr_key, obj_name=f"Settings_Proxy_{obj_name}_Tab_Button"
            )
            self._page_controller.bind_tab(tr_key, btn)
            tabs_hlayout.addWidget(btn)

            if first_key is None:
                first_key = tr_key
                self._page_controller.show(first_key)

        self._page_controller.on_change(lambda _key: self._emit_presence_path())

    def current_presence_subpage(self) -> str:
        key = self._page_controller.current_key()
        if not isinstance(key, str):
            return "Proxy"
        return self._tab_labels_by_key.get(key, key)

    def _emit_presence_path(self) -> None:
        self.presence_path_changed.emit(self.current_presence_subpage())
