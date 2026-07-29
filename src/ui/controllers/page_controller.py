import typing as t

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLayout

from src.ui.widgets.main.containers import MTButtonGroup, MTWidget
from src.ui.widgets.main.text import MTButton


class PageController(QObject):
    page_changed = Signal(object)
    
    def __init__(self, layout: QLayout) -> None:
        self._layout = layout

        self._pages: dict[str, MTWidget] = {}
        self._tabs: dict[str, MTButton] = {}
        self._button_group = MTButtonGroup()
        self._current_page: str | None = None
        self._change_callbacks: list[t.Callable[[str], None]] = []

    def add_page(self, key: str, page: MTWidget, *, obj_name: str | None = None) -> None:
        page.hide()
        self._pages[key] = page
        self._layout.addWidget(page)

        if obj_name:
            page.setObjectName(obj_name)

    def bind_tab(self, key: str, button: MTButton) -> None:
        self._tabs[key] = button
        button.setCheckable(True)
        button.setProperty('pageTab', True)
        self._button_group.addButton(button)
        button.clicked.connect(lambda _checked: self.show(key)) # type: ignore

    def show(self, key: str) -> None:
        if key not in self._pages:
            return
        if self._current_page == key:
            return

        current_page = self.current_page()
        if current_page is not None:
            current_page.setVisible(False)

        self._pages[key].setVisible(True)
        self._current_page = key

        button = self._tabs.get(key)
        if button is not None:
            button.setChecked(True)
        for callback in list(self._change_callbacks):
            callback(key)

    def current_key(self) -> str | None:
        return self._current_page

    def current_page(self) -> MTWidget | None:
        if self._current_page is None:
            return
        return self._pages.get(self._current_page)

    def on_change(self, callback: t.Callable[[str], None]) -> None:
        self._change_callbacks.append(callback)
