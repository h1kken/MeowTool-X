from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout
)
from uis.widgets.custom_widgets import MTButton
from src.uis.proxy.checker import ProxyChecker
from src.uis.roblox.cookie_checker import RobloxCookieChecker
from src.uis.roblox.cookie_sorter import RobloxCookieSorter
from src.uis.roblox.cookie_refresher import RobloxCookieRefresher
from src.uis.roblox.time_booster import RobloxTimeBooster
from src.translation.manager import translator as t
from src.utils.logger import logger
from src.config.manager import config, config_loader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.get('General>Program_Name', default='MeowTool... Meow :3'))
        self.resize(900, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        sidebar = QVBoxLayout()
        main_layout.addLayout(sidebar, 1)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 5)

        PAGES = [
            ('PRX_CHCKR', ProxyChecker),
            ('RBX_C_SRTR', RobloxCookieSorter),
            ('RBX_C_CHCKR', RobloxCookieChecker),
            ('RBX_C_RFRSHR', RobloxCookieRefresher),
            ('RBX_TM_BSTR', RobloxTimeBooster)
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
        btn1.clicked.connect(lambda: t.load_language('ru'))
        btn2.clicked.connect(lambda: t.load_language('en'))
        btn3.clicked.connect(lambda: config_loader.set('Loader>Config On Load', '123'))
        btn4.clicked.connect(lambda: config_loader.set('Loader>Config On Load', '234'))
        
        btn5 = MTButton('Create My Own Language from RU')
        sidebar.addWidget(btn5)
        btn5.clicked.connect(lambda: t.create_my_own_language('ru2', 'ru'))
        btn6 = MTButton('Create My Own Language from EN')
        sidebar.addWidget(btn6)
        btn6.clicked.connect(lambda: t.create_my_own_language('en2', 'en'))
        
        config.set('General>Language', 'en')
        config.set('Proxy>Checker>Main Threads', 20)
        config_loader.set('Saver>Auto Save Changes', True)