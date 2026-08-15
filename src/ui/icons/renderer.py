from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform


@lru_cache(maxsize=128)
def load_icon_pixmap(source: str, w: int = 16, h: int = 16) -> QPixmap:
    return QIcon(source).pixmap(QSize(w, h))


@lru_cache(maxsize=256)
def build_icon_pixmap(source: str, color: str = '#000000', rotation: float = 0, w: int = 16, h: int = 16) -> QPixmap:
    base = load_icon_pixmap(source, w, h)
    if base.isNull():
        return QPixmap()

    pixmap = QPixmap(base.size())
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.drawPixmap(0, 0, base)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()

    if rotation:
        pixmap = pixmap.transformed(
            QTransform().rotate(rotation),
            Qt.TransformationMode.SmoothTransformation,
        )

    return pixmap
