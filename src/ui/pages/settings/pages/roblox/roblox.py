from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QSizePolicy
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.controllers import PageController
from src.ui.widgets import MTButton, MTWidget
from src.ui.pages.settings.pages.roblox import (
    SettingsRobloxCookieSorterPage,
    SettingsRobloxCookieCheckerPage,
    SettingsRobloxCookieRefresherPage,
    SettingsRobloxTimeBoosterPage
)
from src.utils.pyside6 import connect


class SettingsRobloxPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name='Settings_Roblox_Page_Widget')
        main_layout.addWidget(main_widget, alignment=Qt.AlignmentFlag.AlignTop)
        
        tabs_layout = create_layout(LayoutType.HBOX, parent=main_widget)
        
        self._page_controller = PageController(main_layout)
        
        PAGES: list[tuple[Optional[str], Optional[str], Optional[type[QWidget]]]] = [
            ('Cookie_Sorter',    'C_SRTR',   SettingsRobloxCookieSorterPage),
            ('Cookie_Checker',   'C_CHCKR',  SettingsRobloxCookieCheckerPage),
            ('Cookie_Refresher', 'C_RFRSHR', SettingsRobloxCookieRefresherPage),
            ('Time_Booster',     'TM_BSTR',  SettingsRobloxTimeBoosterPage),
            (None,               None,       None),
        ]
        
        for obj_name, tr_key, PageClass in PAGES:
            if PageClass is None:
                tabs_layout.addStretch()
                continue
            
            page = PageClass()
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            self._page_controller.add_page(tr_key, page, object_name=f'Settings_Roblox_{obj_name}_Page')
            
            btn = MTButton(tr_key, obj_name=f'Settings_{obj_name}_Tab_Button')
            connect(btn.clicked, func=lambda _, k=tr_key: self._page_controller.show(k))
            tabs_layout.addWidget(btn)