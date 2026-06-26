from typing import Callable

from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QLayout,
    QWidget,
)


class PageController:
    def __init__(self, layout: QLayout) -> None:
        self._layout = layout
        self._pages: dict[str, QWidget] = {}
        self._tabs: dict[str, QAbstractButton] = {}
        self._button_group = QButtonGroup(exclusive=True)
        self._current_page: str | None = None
        self._change_callbacks: list[Callable[[str], None]] = []

    def add_page(
        self, key: str, page: QWidget, *, obj_name: str | None = None
    ) -> None:
        page.hide()
        self._pages[key] = page
        self._layout.addWidget(page)

        if obj_name:
            page.setObjectName(obj_name)

    def bind_tab(self, key: str, button: QAbstractButton) -> None:
        self._tabs[key] = button
        button.setCheckable(True)
        button.setProperty('pageTab', True)
        self._button_group.addButton(button)
        button.clicked.connect(self._make_show_handler(key))

    def _make_show_handler(self, key: str) -> Callable[[bool], None]:
        def _show_handler(_checked: bool) -> None:
            self.show(key)

        return _show_handler

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

    def current_page(self) -> QWidget | None:
        if self._current_page is None:
            return
        return self._pages.get(self._current_page)

    def on_change(self, callback: Callable[[str], None]) -> None:
        if callable(callback):
            self._change_callbacks.append(callback)

    def preload(
        self,
        *keys: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        if not keys:
            return

        preload_keys = [key for key in keys if key in self._pages]
        if not preload_keys:
            return

        host = self._layout.parentWidget()
        updates_were_enabled = host.updatesEnabled()
        host.setUpdatesEnabled(False)

        current_key = self._current_page

        try:
            total = len(preload_keys)
            for index, key in enumerate(preload_keys, start=1):
                page = self._pages[key]
                was_visible = page.isVisible()
                page.ensurePolished()
                if (layout := page.layout()) is not None:
                    layout.activate()

                if not was_visible:
                    page.setVisible(True)
                    QApplication.processEvents()
                    page.setVisible(False)

                if callable(progress_callback):
                    progress_callback(index, total, key)
        finally:
            if current_key is not None and current_key in self._pages:
                for key, page in self._pages.items():
                    page.setVisible(key == current_key)
                button = self._tabs.get(current_key)
                if button is not None:
                    button.setChecked(True)

            host.setUpdatesEnabled(updates_were_enabled)
