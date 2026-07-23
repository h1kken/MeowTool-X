from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import src.app.context as ctx
from src.app.bootstrap import bootstrap
from src.app.constants import PROGRAM_TITLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(PROGRAM_TITLE)
    
    bootstrap(app)

    ctx.services.window.show()
    
    ctx.services.discord_rpc.start()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
