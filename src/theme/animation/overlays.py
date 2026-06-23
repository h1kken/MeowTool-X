from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from math import cos, radians, sin

from PySide6.QtGui import QBrush, QColor, QGradient, QLinearGradient, QPainter, QPainterPath, QPainterPathStroker
from PySide6.QtWidgets import QWidget

from src.theme.constants import GRADIENT_DIRECTIONS

def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class DashBorderOverlay(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        self._color = QColor("#ffffff")
        self._width = 1.0
        self._radius = 6.0
        self._dash_pattern: list[float] = [4.0, 2.0]
        self._dash_offset = 0.0
        self._inset = 0.5
        self._pen_style = Qt.PenStyle.CustomDashLine
        self._mode = 'dash'
        self._gradient_stops: list[tuple[float, QColor]] = [
            (0.0, QColor('#ffffff')),
            (1.0, QColor('#ffffff')),
        ]
        self._gradient_direction = 'horizontal'
        self._gradient_angle: float | None = None
        self._gradient_phase = 0.0
        self._opacity = 1.0

    def configure(
        self,
        *,
        color: QColor,
        width: float,
        radius: float,
        dash_pattern: list[float],
        inset: float,
        pen_style: Qt.PenStyle,
        opacity: float = 1.0,
    ) -> None:
        self._mode = 'dash'
        self._color = QColor(color)
        self._width = max(0.5, float(width))
        self._radius = max(0.0, float(radius))
        self._dash_pattern = [max(0.1, float(v)) for v in dash_pattern] or [4.0, 2.0]
        self._inset = float(inset)
        self._pen_style = pen_style
        self._opacity = max(0.0, min(float(opacity), 1.0))
        self.update()

    def set_color(self, value: QColor) -> None:
        self._color = QColor(value)
        self.update()

    def color(self) -> QColor:
        return QColor(self._color)

    def set_dash_offset(self, value: float) -> None:
        self._dash_offset = float(value)
        self.update()

    def configure_gradient(
        self,
        *,
        width: float,
        radius: float,
        inset: float,
        direction: str,
        stops: list[tuple[float, QColor]],
        pen_style: Qt.PenStyle,
        dash_pattern: list[float],
        opacity: float = 1.0,
    ) -> None:
        self._mode = 'gradient'
        self._width = max(0.5, float(width))
        self._radius = max(0.0, float(radius))
        self._inset = float(inset)
        self._gradient_direction = str(direction or 'horizontal')
        self._gradient_angle = None
        self._gradient_stops = [
            (_clamp01(pos), QColor(color))
            for pos, color in stops
        ] or [(0.0, QColor('#ffffff')), (1.0, QColor('#ffffff'))]
        self._pen_style = pen_style
        self._dash_pattern = [max(0.1, float(v)) for v in dash_pattern] or [4.0, 2.0]
        self._opacity = max(0.0, min(float(opacity), 1.0))
        self.update()

    def set_gradient_angle(self, value: float | None) -> None:
        self._gradient_angle = None if value is None else float(value)
        self.update()

    def set_gradient_phase(self, value: float) -> None:
        self._gradient_phase = float(value)
        self.update()

    def gradient_phase(self) -> float:
        return float(self._gradient_phase)

    def set_gradient_stops(self, stops: list[tuple[float, QColor]]) -> None:
        self._gradient_stops = [
            (_clamp01(pos), QColor(color))
            for pos, color in stops
        ] or [(0.0, QColor('#ffffff')), (1.0, QColor('#ffffff'))]
        self.update()

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(float(value), 1.0))
        self.update()

    def opacity(self) -> float:
        return float(self._opacity)

    def paintEvent(self, _) -> None:
        if self._width <= 0.0 or self._opacity <= 0.0:
            return

        painter = QPainter(self)
        if not painter.isActive():
            return

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setOpacity(self._opacity)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            border_offset = max(0.0, (self._width / 2.0) + self._inset)
            rect = QRectF(self.rect()).adjusted(border_offset, border_offset, -border_offset, -border_offset)
            if rect.width() <= 0.0 or rect.height() <= 0.0:
                return

            radius = min(self._radius, rect.width() / 2.0, rect.height() / 2.0)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            stroke = self._build_stroke_path(path)
            painter.fillPath(stroke, self._build_brush())
        finally:
            painter.end()

    def _build_stroke_path(self, path: QPainterPath) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(self._width)
        stroker.setCapStyle(Qt.PenCapStyle.FlatCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if self._pen_style == Qt.PenStyle.CustomDashLine:
            stroker.setDashPattern(self._dash_pattern)
            stroker.setDashOffset(self._dash_offset)
        return stroker.createStroke(path)

    def _build_brush(self) -> QBrush:
        if self._mode == 'gradient':
            gradient = QLinearGradient()
            gradient.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
            gradient.setSpread(QGradient.Spread.RepeatSpread)

            if isinstance(self._gradient_angle, float):
                x1, y1, x2, y2 = _gradient_points_from_angle(self._gradient_angle)
            else:
                x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(
                    self._gradient_direction,
                    GRADIENT_DIRECTIONS['horizontal'],
                )
            dx = x2 - x1
            dy = y2 - y1
            phase = self._gradient_phase
            gradient.setStart(x1 + (dx * phase), y1 + (dy * phase))
            gradient.setFinalStop(x2 + (dx * phase), y2 + (dy * phase))
            for pos, color in self._gradient_stops:
                gradient.setColorAt(_clamp01(pos), QColor(color))

            return QBrush(gradient)

        return QBrush(QColor(self._color))

    def _opaque_color(self, color: QColor) -> QColor:
        result = QColor(color)
        result.setAlpha(255)
        return result


def _gradient_points_from_angle(angle_degrees: float) -> tuple[float, float, float, float]:
    angle = radians(float(angle_degrees) % 360.0)
    dx = cos(angle) * 0.5
    dy = sin(angle) * 0.5
    return (0.5 - dx, 0.5 - dy, 0.5 + dx, 0.5 + dy)


