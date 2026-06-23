from __future__ import annotations

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QStyle, QStyleOption, QWidget


def configure_painter(
    painter: QPainter,
    *,
    antialias: bool = True,
    text_antialias: bool = False,
    smooth_pixmap: bool = False,
) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, antialias)
    if text_antialias:
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    if smooth_pixmap:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)


def new_widget_painter(
    widget: QWidget,
    *,
    antialias: bool = True,
    text_antialias: bool = False,
    smooth_pixmap: bool = False,
) -> QPainter:
    painter = QPainter(widget)
    configure_painter(
        painter,
        antialias=antialias,
        text_antialias=text_antialias,
        smooth_pixmap=smooth_pixmap,
    )
    return painter


def draw_widget_background(widget: QWidget, painter: QPainter) -> None:
    has_box_theme = getattr(widget, 'has_box_theme', None)
    draw_box_theme = getattr(widget, 'draw_box_theme', None)
    if callable(has_box_theme) and has_box_theme() and callable(draw_box_theme):
        draw_box_theme(painter)
        return

    option = QStyleOption()
    option.initFrom(widget)
    widget.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, widget)


__all__ = ('configure_painter', 'new_widget_painter', 'draw_widget_background')
