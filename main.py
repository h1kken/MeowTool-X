import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.app.bootstrap import bootstrap
from src.app.constants import PROGRAM_NAME
from src.ui.windows.main_window import MainWindow


def _finish_startup(window: MainWindow) -> None:
    window.resume_theme_events()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName(PROGRAM_NAME)
    

    services = bootstrap(app)

    services.window.show()
    services.discord_rpc.start()
    
    QTimer.singleShot(0, lambda: _finish_startup(services.window))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
