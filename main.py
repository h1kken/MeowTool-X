import faulthandler
faulthandler.enable()

import sys

from PySide6.QtWidgets import QApplication

from src.bootstrap import AppBootstrap
from src.utils.constants import PROGRAM_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(PROGRAM_NAME)
    AppBootstrap().run()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
