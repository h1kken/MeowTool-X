from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout
)
from src.services.roblox.sorter import RobloxCookieSorter
from src.ui.widgets.custom_widgets import MTButton
from src.ui.proxy.checker_window import ProxyCheckerWindow
from src.ui.roblox.cookie_checker_window import RobloxCookieCheckerWindow
from src.ui.roblox.cookie_sorter_window import RobloxCookieSorterWindow
from src.ui.roblox.cookie_refresher_window import RobloxCookieRefresherWindow
from src.ui.roblox.time_booster_window import RobloxTimeBoosterWindow
from src.translation.manager import translator as t
from src.utils.logging import logger
from src.utils.consts import WINDOW_X, WINDOW_Y
from src.config.manager import config, config_loader
from src.utils.filesystem import create_start_folders_and_files, count_lines_in_file


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
            ('PRX_CHCKR', ProxyCheckerWindow),
            ('RBX_C_SRTR', RobloxCookieSorterWindow),
            ('RBX_C_CHCKR', RobloxCookieCheckerWindow),
            ('RBX_C_RFRSHR', RobloxCookieRefresherWindow),
            ('RBX_TM_BSTR', RobloxTimeBoosterWindow)
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
        btn5.clicked.connect(lambda: t.create_language('ru2', 'ru'))
        btn6 = MTButton('Create My Own Language from EN')
        sidebar.addWidget(btn6)
        btn6.clicked.connect(lambda: t.create_language('en2', 'en'))
        
        config.set('General>Language', 'en')
        config.set('Proxy>Checker>Main Threads', 20)
        config_loader.set('Saver>Auto Save Changes', True)
        
        ### Test database
        from src.database.manager import Database
        from src.database.models.roblox.cookie_checker.account import BaseCookieChecker, Account
        
        db = Database('sqlite:///123.db')
        db.create_tables(BaseCookieChecker)
        
        acc1 = Account(p_valid=True, p_id=123123123, p_name='123123123', p_cookie='_||_123123123')
        acc2 = Account(p_valid=True, p_id=234234234, p_name='234234234', p_cookie='_|_234234234')
        acc3 = Account(p_valid=True, p_id=345345345, p_name='345345345', p_cookie='_|345|_345345345')
        
        with db.session_scope() as session:
            session.add_all([acc1, acc2, acc3])
        
        ### Test counting lines in big files
        count_in_file = Path(r'Roblox\Cookie Checker\cookies.txt')
        logger.debug(f'{count_lines_in_file(count_in_file)} lines in {count_in_file}')
        