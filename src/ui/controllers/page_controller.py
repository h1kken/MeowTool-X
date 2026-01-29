from typing import Optional
from PySide6.QtWidgets import QLayout, QWidget


class PageController:
    def __init__(self, layout: QLayout):
        self._layout = layout
        self._pages: dict[str, QWidget] = {}
        self._current_page: Optional[str] = None

    def add_page(self, key: str, page: QWidget, *, object_name: Optional[str] = None):
        self._pages[key] = page
        self._layout.addWidget(page)
        
        if object_name:
            page.setObjectName(object_name)
            
        page.hide()

    def show(self, key: str):
        if self._current_page == key:
            return
        
        if (p := self._pages.get(self._current_page)):
            p.setVisible(False)
        
        self._pages[key].setVisible(True)
        self._current_page = key