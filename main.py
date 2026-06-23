import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.config.manager import config
from src.db import initialize_database
from src.translation.constants import SYSTEM_LOCALE
from src.translation.manager import translator
from src.ui.windows.main_window import MainWindow
from src.utils.constants import (
    PATH_DEFAULT_THEME,
    PROGRAM_NAME,
)


def _finish_startup(window: MainWindow) -> None:
    window.preload_settings_pages()
    window.start_discord_presence()
    window.resume_theme_events()


def main():
    # app init
    app = QApplication(sys.argv)
    app.setApplicationName(PROGRAM_NAME)
    
    # db init
    initialize_database()
    
    # translation load
    translator.load_language(
        str(config.get("General>Language", default=SYSTEM_LOCALE)).strip()
    )

    # window init
    window = MainWindow()
    window.build_pages()
    window.init_runtime_controllers()
    window.initialize_theme_manager()
    window.apply_startup_theme(str(config.get("General>Theme", default=PATH_DEFAULT_THEME.stem)).strip())
    window.show()
    QTimer.singleShot(0, lambda: _finish_startup(window))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
