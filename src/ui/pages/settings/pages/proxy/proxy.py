from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QSizePolicy
from src.ui.widgets import MTButton, MTWidget
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.controllers import PageController
from src.ui.pages.settings.pages.proxy import SettingsProxyCheckerPage
from src.utils.pyside6 import connect


class SettingsProxyPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        main_widget = MTWidget(obj_name='Settings_Proxy_Page_Widget')
        main_layout.addWidget(main_widget, alignment=Qt.AlignmentFlag.AlignTop)
        
        tabs_hlayout = create_layout(LayoutType.HBOX, parent=main_widget)
        
        self._page_controller = PageController(main_layout)
        
        PAGES: list[tuple[Optional[str], Optional[str], Optional[type[QWidget]]]] = [
            ('Checker', 'CHCKR', SettingsProxyCheckerPage),
            (None,      None,    None),
        ]
        
        for obj_name, tr_key, PageClass in PAGES:
            if PageClass is None:
                tabs_hlayout.addStretch()
                continue
            
            page = PageClass()
            page.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            self._page_controller.add_page(tr_key, page, object_name=f'Settings_Proxy_{obj_name}_Page')
            
            btn = MTButton(tr_key, obj_name=f'Settings_{obj_name}_Tab_Button')
            connect(btn.clicked, func=lambda _, k=tr_key: self._page_controller.show(k))
            tabs_hlayout.addWidget(btn)