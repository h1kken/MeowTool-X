from typing import Optional
from PySide6.QtWidgets import QMainWindow, QWidget, QSizePolicy
from src.ui.pages import (
    ProxyCheckerPage,
    RobloxCookieCheckerPage,
    RobloxCookieSorterPage,
    RobloxCookieRefresherPage,
    RobloxTimeBoosterPage,
    SettingsPage,
    AboutPage,
)
from src.ui.widgets import MTButton
from src.ui.controllers import PageController
from src.ui.layouts.factory import create_layout, LayoutType
from src.utils.filesystem import load_json
from src.utils.debug import dump_object_tree
from src.utils.pyside6 import connect
from src.utils.consts import WINDOW_X, WINDOW_Y, DEFAULT_THEME, IS_LAUNCHED_WITH_CONSOLE
from src.theme.manager import ThemeManager
from src.ui.widgets.custom_widgets import MTWidget
# from src.utils.pyside6 import connect
# from src.theme.animation.manager import AnimationManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setObjectName('Main_Window')
        self.setWindowTitle('MeowTool... Meow :3')
        self.resize(WINDOW_X, WINDOW_Y)
        
        self._build_ui()
        
        if IS_LAUNCHED_WITH_CONSOLE: # debug only
            self.setStyleSheet('* { border: 1px solid red; }')
            dump_object_tree(self)
        
        # self._animation_manager = AnimationManager(
        #     self.centralWidget()
        # )
        
        self._theme_manager = ThemeManager(
            self.centralWidget(),
            load_json(DEFAULT_THEME)
        )
        
        # connect(
        #     self._theme_manager.theme_changed,
        #     func=self._animation_manager.load
        # )
        
        self._theme_manager.load(DEFAULT_THEME)
        self._theme_manager.apply()
    
    def _build_ui(self):
        central_widget = MTWidget(obj_name='Central_Widget')
        self.setCentralWidget(central_widget)
        
        main_layout = create_layout(LayoutType.HBOX, parent=central_widget)
        
        sidebar_widget = MTWidget(obj_name='Sidebar_Widget')
        sidebar_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(sidebar_widget)

        sidebar_buttons_layout = create_layout(LayoutType.VBOX, parent=sidebar_widget)

        main_content = MTWidget(obj_name='Main_Content_Widget')
        main_content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(main_content)

        pages_layout = create_layout(LayoutType.VBOX, parent=main_content)
        self._page_controller = PageController(pages_layout)
        
        PAGES: list[tuple[Optional[str], Optional[str], Optional[type[QWidget]]]] = [
            ('Proxy_Checker',           'PRX_CHCKR',    ProxyCheckerPage),
            ('Roblox_Cookie_Sorter',    'RBX_C_SRTR',   RobloxCookieSorterPage),
            ('Roblox_Cookie_Checker',   'RBX_C_CHCKR',  RobloxCookieCheckerPage),
            ('Roblox_Cookie_Refresher', 'RBX_C_RFRSHR', RobloxCookieRefresherPage),
            ('Roblox_Time_Booster',     'RBX_TM_BSTR',  RobloxTimeBoosterPage),
            (None,                      None,           None),
            ('Settings',                'STNGS',        SettingsPage),
            ('About',                   'ABT',          AboutPage),
        ]

        for obj_name, tr_key, PageClass in PAGES:
            if PageClass is None:
                sidebar_buttons_layout.addStretch()
                continue
            
            page = PageClass()
            self._page_controller.add_page(tr_key, page, object_name=f'Main_{obj_name}_Page')
            
            btn = MTButton(tr_key, obj_name=f'Sidebar_{obj_name}_Tab_Button')
            connect(btn.clicked, func=lambda _, k=tr_key: self._page_controller.show(k))
            sidebar_buttons_layout.addWidget(btn)
