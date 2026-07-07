from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import src.app.context as ctx
from src.app.bootstrap import bootstrap
from src.app.constants import PROGRAM_NAME

if TYPE_CHECKING:
    from src.ui.windows.main_window import MainWindow


def _finish_startup(window: MainWindow) -> None:
    window.resume_theme_events()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName(PROGRAM_NAME)
    
    ctx.services = bootstrap(app)

    ctx.services.window.show()
    ctx.services.discord_rpc.start()
    
    QTimer.singleShot(0, lambda: _finish_startup(ctx.services.window))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
