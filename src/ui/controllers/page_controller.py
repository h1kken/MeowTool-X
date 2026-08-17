from __future__ import annotations

import typing as t

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLayout

from src.ui.widgets.common import MTButton, MTButtonGroup, MTWidget


class HasPageController(t.Protocol):
    @property
    def page_controller(self) -> PageController: ...


@dataclass(frozen=True, slots=True)
class _PageEntry:
    name: str
    page: MTWidget
    button: MTButton


class PageController(QObject):
    pageChanged = Signal(tuple)
    
    def __init__(
        self,
        layout: QLayout,
        *,
        parent_page_controller: PageController | None = None
    ) -> None:
        super().__init__()
        self._layout = layout
        self._parent_controller = parent_page_controller
        self._child_controllers: dict[str, PageController] = {}
        
        self.set_child_controller

        self._pages: dict[str, _PageEntry] = {}
        self._button_group = MTButtonGroup()
        
        self._connect_signals()
    
    def _connect_signals(self) -> None:
        if self._parent_controller is not None:
            self.pageChanged.connect(self._parent_controller._on_child_page_changed)
    
    @property
    def current(self) -> _PageEntry:
        return self._current
    
    @property
    def parent_controller(self) -> PageController | None:
        return self._parent_controller

    @property
    def child_controllers(self) -> dict[str, PageController]:
        return self._child_controllers

    def set_child_controller(self, key: str, controller: PageController) -> None:
        self._child_controllers[key] = controller

    def add_page(self, key: str, name: str, page: MTWidget, button: MTButton) -> None:
        button.setCheckable(True)
        button.clicked.connect(lambda _checked: self.show(key)) # type: ignore
        self._button_group.addButton(button)
        
        page_entry = _PageEntry(
            name=name,
            page=page,
            button=button,
        )
        
        self._pages[key] = page_entry
        self._layout.addWidget(page)
        
        if len(self._pages) == 1:
            self._current = page_entry
            page.show()
            button.setChecked(True)
        else:
            page.hide()

    def show(self, key: str) -> None:
        req = self._pages[key]
        if self._current is req:
            return

        self._current.page.hide()
        req.page.show()
        req.button.setChecked(True)
        self._current = req
        self.pageChanged.emit((req.name,))

    def _on_child_page_changed(self, child_paths: tuple[str, ...]) -> None:
        self.pageChanged.emit((self.current.name, *child_paths))
