from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPainterPathStroker
from PySide6.QtWidgets import QWidget


class DashBorderOverlay(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        self._color = QColor('#ffffff')
        self._width = 1.0
        self._radius = 6.0
        self._dash_pattern: list[float] = [4.0, 2.0]
        self._dash_offset = 0.0
        self._inset = 0.5
        self._pen_style = Qt.PenStyle.CustomDashLine
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
            painter.fillPath(stroke, QBrush(QColor(self._color)))
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
