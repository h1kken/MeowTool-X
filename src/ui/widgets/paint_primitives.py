from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath


def parse_pen_style(value: object) -> Qt.PenStyle:
    text = str(value or 'solid').strip().lower().replace('_', '-')
    match text:
        case 'none' | 'no' | 'transparent':
            return Qt.PenStyle.NoPen
        case 'dash' | 'dashed':
            return Qt.PenStyle.DashLine
        case 'dot' | 'dotted':
            return Qt.PenStyle.DotLine
        case 'dash-dot' | 'dashdot':
            return Qt.PenStyle.DashDotLine
        case 'dash-dot-dot' | 'dashdotdot':
            return Qt.PenStyle.DashDotDotLine
        case _:
            return Qt.PenStyle.SolidLine


def parse_non_negative_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    text = str(value or '').strip().lower()
    if text.endswith('px'):
        text = text[:-2].strip()
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def resolve_uniform_radius(rect: QRectF, value: object) -> float:
    text = str(value or '').strip().lower()
    max_radius = max(0.0, min(rect.width(), rect.height()) / 2.0)
    if not text:
        return 0.0
    if text.endswith('%'):
        try:
            return max(
                0.0,
                min(
                    max_radius,
                    (min(rect.width(), rect.height()) * float(text[:-1].strip())) / 100.0,
                ),
            )
        except ValueError:
            return 0.0
    return max(0.0, min(max_radius, parse_non_negative_float(text)))


def rounded_rect_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    if rect.isValid() and rect.width() > 0 and rect.height() > 0:
        path.addRoundedRect(rect, radius, radius)
    return path


def resolve_fill_brush(
    rect: QRectF,
    *,
    color: QColor | None = None,
    empty: object = Qt.BrushStyle.NoBrush,
) -> object:
    _ = rect
    if isinstance(color, QColor) and color.isValid():
        return color
    return empty
