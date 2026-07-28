from functools import lru_cache
import typing as t

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QWidget

SETTING_ROW_HEIGHT = 0
SETTING_ROW_GAP = 0
SLIDER_COMPACT_PART_HEIGHT = 0
COLLAPSIBLE_TOGGLE_BUTTON_SIZE = 20
COLLAPSIBLE_TOGGLE_ICON_SIZE = 18


@lru_cache(maxsize=64)
def icon(source: str, color_name: str, rotation: float, size: int) -> QIcon:
    base_pixmap = QIcon(source).pixmap(QSize(size, size))
    if base_pixmap.isNull():
        return QIcon()

    tinted_pixmap = QPixmap(base_pixmap.size())
    tinted_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted_pixmap)
    painter.drawPixmap(0, 0, base_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted_pixmap.rect(), QColor(color_name))
    painter.end()

    rotated_pixmap = tinted_pixmap.transformed(
        QTransform().rotate(rotation), Qt.TransformationMode.SmoothTransformation
    )
    return QIcon(rotated_pixmap)


def repolish(widget: QWidget) -> None:
    style = widget.style()
    if not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
        widget.update()
        return

    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def config_int(value: t.Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def config_float(value: t.Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
