from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel


class MTImage(QLabel):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
        source: Path | None = None,
        fixed_height: int | None = None,
    ) -> None:
        super().__init__(parent)

        if obj_name:
            self.setObjectName(obj_name)

        if fixed_height is not None:
            self.setFixedHeight(fixed_height)

        if source is not None:
            self.setPixmap(QPixmap(str(source)))
