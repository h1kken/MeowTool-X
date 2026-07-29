from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QWidget

SETTING_ROW_HEIGHT = 0
SETTING_ROW_GAP = 0
SLIDER_COMPACT_PART_HEIGHT = 0
COLLAPSIBLE_TOGGLE_BUTTON_SIZE = 20
COLLAPSIBLE_TOGGLE_ICON_SIZE = 18


@lru_cache(maxsize=128)
def _load_pixmap(source: str, size: int) -> QPixmap:
    pixmap = QIcon(source).pixmap(QSize(size, size))
    return pixmap


@lru_cache(maxsize=256)
def icon(source: str, color_name: str, rotation: float, size: int) -> QIcon:
    base_pixmap = _load_pixmap(source, size)

    if base_pixmap.isNull():
        return QIcon()

    tinted_pixmap = QPixmap(base_pixmap.size())
    tinted_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted_pixmap)
    painter.drawPixmap(0, 0, base_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted_pixmap.rect(), QColor(color_name))
    painter.end()

    if rotation:
        tinted_pixmap = tinted_pixmap.transformed(
            QTransform().rotate(rotation),
            Qt.TransformationMode.SmoothTransformation,
        )

    return QIcon(tinted_pixmap)


def repolish(widget: QWidget) -> None:
    if not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
        widget.update()
        return

    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
