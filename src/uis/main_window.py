from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout
)
from src.uis.widgets.custom_widgets import MTButton
from src.uis.proxy.checker import ProxyChecker
from src.uis.roblox.cookie_checker import RobloxCookieChecker
from src.uis.roblox.cookie_sorter import RobloxCookieSorter
from src.uis.roblox.cookie_refresher import RobloxCookieRefresher
from src.uis.roblox.time_booster import RobloxTimeBooster
from src.translation.manager import translator as t
from src.utils.logger import logger
from src.utils.consts import WINDOW_X, WINDOW_Y
from src.config.manager import config, config_loader
from src.utils.file import create_start_folders_and_files


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        window_title = config.get('General>Program Name', default='MeowTool... Meow :3')
        self.setWindowTitle(window_title)
        logger.info(f'Setted window title to: {window_title}')
        
        self.resize(WINDOW_X, WINDOW_Y)
        logger.info(f'Setted window resolution to: {WINDOW_X}x{WINDOW_Y}')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        create_start_folders_and_files()

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
        
        ###
        from src.database.manager import Database
        from src.database.models.roblox.cookie_checker.account import BaseCookieChecker, Account
        
        db = Database('sqlite:///123.db')
        db.create_tables(BaseCookieChecker)
        
        acc1 = Account(p_valid=True, p_id=123123123, p_name='123123123', p_cookie='_||_123123123')
        acc2 = Account(p_valid=True, p_id=234234234, p_name='234234234', p_cookie='_|_234234234')
        acc3 = Account(p_valid=True, p_id=345345345, p_name='345345345', p_cookie='_|345|_345345345')
        
        with db.session_scope() as session:
            session.add_all([acc1, acc2, acc3])
        