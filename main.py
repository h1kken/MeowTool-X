from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import src.app.context as ctx
from src.app.bootstrap import bootstrap
from src.app.constants import PROGRAM_NAME


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName(PROGRAM_NAME)
    
    bootstrap(app)

    ctx.services.window.show()
    QTimer.singleShot(0, lambda: ctx.services.window.resume_theme_events)
    
    ctx.services.discord_rpc.start()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
