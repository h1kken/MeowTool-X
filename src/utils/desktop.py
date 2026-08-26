import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


class Desktop:
    @staticmethod
    def open_url(url: str) -> bool:
        return QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def open_file_location(path: Path) -> bool:
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', str(path)])
            return True

        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
