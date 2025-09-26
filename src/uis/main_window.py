from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout
)

from .custom_widgets import MTButton
from .proxy import ProxyChecker
from .roblox import (
    RobloxCookieSorter,
    RobloxCookieChecker,
    RobloxCookieRefresher,
    RobloxTimeBooster
)
from ..config.manager import config, config_loader
from ..translation.manager import translator as t
from ..utils import logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.get('General.Program_Name', default='MeowTool... Meow :3'))
        self.resize(900, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        sidebar = QVBoxLayout()
        main_layout.addLayout(sidebar, 1)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 5)

        PAGES = [
            ('page_proxy_checker', ProxyChecker),
            ('page_roblox_cookie_sorter', RobloxCookieSorter),
            ('page_roblox_cookie_checker', RobloxCookieChecker),
            ('page_roblox_cookie_refresher', RobloxCookieRefresher),
            ('page_roblox_time_booster', RobloxTimeBooster)
        ]

        for index, (title, page) in enumerate(PAGES):
            self.stack.addWidget(page())
            btn = MTButton(title)
            sidebar.addWidget(btn)
            btn.clicked.connect(lambda _, i=index: self.stack.setCurrentIndex(i))
            
        sidebar.addStretch()
        btn1 = MTButton('Russian')
        btn2 = MTButton('English')
        btn3 = MTButton('Set to 123')
        btn4 = MTButton('Set to 234')
        sidebar.addWidget(btn1)
        sidebar.addWidget(btn2)
        sidebar.addWidget(btn3)
        sidebar.addWidget(btn4)
        sidebar.addStretch()
        btn1.clicked.connect(lambda: t.load_language('ru_RU'))
        btn2.clicked.connect(lambda: t.load_language('en_US'))
        btn3.clicked.connect(lambda: config_loader.set('Loader.Config_On_Load', '123'))
        btn4.clicked.connect(lambda: config_loader.set('Loader.Config_On_Load', '234'))
