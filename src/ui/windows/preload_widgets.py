from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.theme.colors import to_qcolor
from src.theme.rainbow.palette import sample_rainbow_color
from src.ui.widgets import MTWidget
from src.utils.constants import PRELOAD_RING_MIN_SIZE, PRELOAD_RING_VALUE_FONT_SIZE
from src.utils.preload import coerce_qcolor, resolve_preload_window_radius_px


class StartupRingWidget(MTWidget):
    def __init__(self, *, image_path: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, obj_name='Preload_Ring')
        self._progress = 0.0
        self._display_progress = 0.0
        self._default_pixmap = QPixmap(str(image_path)) if isinstance(image_path, Path) and image_path.exists() else QPixmap()
        self._pixmap = QPixmap(self._default_pixmap)
        self._default_halo_color = QColor(Qt.GlobalColor.transparent)
        self._default_track_color = QColor(Qt.GlobalColor.transparent)
        self._default_progress_color = QColor(Qt.GlobalColor.transparent)
        self._default_inner_color = QColor(Qt.GlobalColor.transparent)
        self._default_inner_glow_color = QColor(Qt.GlobalColor.transparent)
        self._default_value_color = QColor(Qt.GlobalColor.transparent)
        self._halo_color = QColor(self._default_halo_color)
        self._track_color = QColor(self._default_track_color)
        self._progress_color = QColor(self._default_progress_color)
        self._inner_color = QColor(self._default_inner_color)
        self._inner_glow_color = QColor(self._default_inner_glow_color)
        self._value_color = QColor(self._default_value_color)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(260)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_progress_animated)
        self._rainbow_enabled = False
        self._rainbow_duration_ms = 5000
        self._rainbow_saturation = 0.6
        self._rainbow_palette = 'Pastel'
        self._rainbow_timer = QVariantAnimation(self)
        self._rainbow_timer.setStartValue(0.0)
        self._rainbow_timer.setEndValue(1.0)
        self._rainbow_timer.setDuration(1)
        self._rainbow_timer.setLoopCount(-1)
        self._rainbow_timer.valueChanged.connect(lambda *_: self.update())
        self.setFixedSize(PRELOAD_RING_MIN_SIZE, PRELOAD_RING_MIN_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_progress(self, value: float) -> None:
        target = max(0.0, min(100.0, float(value)))
        if abs(target - self._progress) < 0.01:
            return

        self._progress = target
        self._animation.stop()
        self._animation.setStartValue(self._display_progress)
        self._animation.setEndValue(target)
        self._animation.start()

    def _on_progress_animated(self, value: float) -> None:
        self._display_progress = float(value)
        self.update()

    def reset_theme(self) -> None:
        self._pixmap = QPixmap(self._default_pixmap)
        self._halo_color = QColor(self._default_halo_color)
        self._track_color = QColor(self._default_track_color)
        self._progress_color = QColor(self._default_progress_color)
        self._inner_color = QColor(self._default_inner_color)
        self._inner_glow_color = QColor(self._default_inner_glow_color)
        self._value_color = QColor(self._default_value_color)
        self.update()

    def set_progress_rainbow(self, enabled: bool, duration_ms: int | float, saturation: float = 0.6, palette: str = 'Pastel') -> None:
        self._rainbow_enabled = bool(enabled)
        self._rainbow_duration_ms = max(1, int(round(float(duration_ms))))
        self._rainbow_saturation = max(0.0, min(float(saturation), 1.0))
        self._rainbow_palette = str(palette or 'Pastel').strip() or 'Pastel'
        if self._rainbow_enabled:
            self._rainbow_timer.setDuration(self._rainbow_duration_ms)
            self._rainbow_timer.start()
        else:
            self._rainbow_timer.stop()
        self.update()

    def current_part_color(self, part: str) -> QColor | None:
        mapping = {
            'halo': self._halo_color,
            'track': self._track_color,
            'progress': self._progress_color,
            'inner': self._inner_color,
            'value': self._value_color,
        }
        color = mapping.get(str(part).strip())
        if isinstance(color, QColor) and color.isValid():
            return QColor(color)
        return None

    def set_part_color(self, part: str, value: QColor | str) -> bool:
        color = to_qcolor(value)
        if color is None:
            return False

        key = str(part).strip()
        if key == 'halo':
            self._halo_color = color
        elif key == 'track':
            self._track_color = color
        elif key == 'progress':
            self._progress_color = color
        elif key == 'inner':
            self._inner_color = color
        elif key == 'value':
            self._value_color = color
        else:
            return False
        self.update()
        return True

    def apply_theme(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return

        halo_data = data.get('halo')
        if isinstance(halo_data, dict):
            self._halo_color = coerce_qcolor(halo_data.get('color'), self._halo_color)

        track_data = data.get('track')
        if isinstance(track_data, dict):
            self._track_color = coerce_qcolor(track_data.get('color'), self._track_color)

        progress_data = data.get('progress')
        if isinstance(progress_data, dict):
            self._progress_color = coerce_qcolor(progress_data.get('color'), self._progress_color)

        inner_data = data.get('inner')
        if isinstance(inner_data, dict):
            self._inner_color = coerce_qcolor(inner_data.get('color'), self._inner_color)
            self._inner_glow_color = coerce_qcolor(inner_data.get('glow_color'), self._inner_glow_color)

        value_data = data.get('value')
        if isinstance(value_data, dict):
            self._value_color = coerce_qcolor(value_data.get('color'), self._value_color)

        icon_data = data.get('icon')
        if isinstance(icon_data, dict):
            source = icon_data.get('source')
            if isinstance(source, str) and source.strip():
                pixmap = QPixmap(source)
                if not pixmap.isNull():
                    self._pixmap = pixmap
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        base_rect = QRectF(self.rect()).adjusted(16.5, 16.5, -16.5, -16.5)
        center = base_rect.center()
        radius = min(base_rect.width(), base_rect.height()) / 2.0

        halo_pen = QPen(self._halo_color, 22.0)
        halo_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        halo_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(halo_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - 11.0, radius - 11.0)

        track_pen = QPen(self._track_color, 16.0)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        track_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(track_pen)
        painter.drawEllipse(base_rect)

        progress_pen = QPen(self._current_progress_color(), 16.0)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        progress_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(progress_pen)
        span_angle = int(-(self._display_progress / 100.0) * 360.0 * 16.0)
        painter.drawArc(base_rect, 90 * 16, span_angle)

        inner_rect = QRectF(base_rect).adjusted(26.0, 26.0, -26.0, -26.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._inner_color)
        painter.drawEllipse(inner_rect)

        painter.setBrush(self._inner_glow_color)
        painter.drawEllipse(QRectF(inner_rect).adjusted(12.0, 12.0, -12.0, -12.0))

        if not self._pixmap.isNull():
            icon_size = max(44, int(inner_rect.width() * 0.34))
            icon_rect = inner_rect.adjusted(
                (inner_rect.width() - icon_size) / 2.0,
                inner_rect.height() * 0.15,
                -((inner_rect.width() - icon_size) / 2.0),
                -(inner_rect.height() * 0.35),
            )
            pixmap = self._pixmap.scaled(
                icon_rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            top_left = QPointF(
                icon_rect.center().x() - (pixmap.width() / 2.0),
                icon_rect.center().y() - (pixmap.height() / 2.0),
            )
            painter.drawPixmap(top_left, pixmap)

        value_rect = QRectF(inner_rect).adjusted(18.0, inner_rect.height() * 0.56, -18.0, -18.0)
        font = QFont(self.font())
        font.setPointSize(PRELOAD_RING_VALUE_FONT_SIZE)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self._value_color)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, f'{int(round(self._display_progress))}%')

    def _current_progress_color(self) -> QColor:
        if not self._rainbow_enabled:
            return QColor(self._progress_color)

        return sample_rainbow_color(
            self._rainbow_phase(),
            palette=self._rainbow_palette,
            saturation=self._rainbow_saturation,
        )

    def _rainbow_phase(self) -> float:
        current_time = self._rainbow_timer.currentTime()
        if self._rainbow_duration_ms <= 0:
            return 0.0
        return (float(current_time) % float(self._rainbow_duration_ms)) / float(self._rainbow_duration_ms)


class _PreloadWindowFrame(MTWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, obj_name='Preload_Window')
        self._styles: dict[str, Any] = {}
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def apply_frame_theme(self, styles: dict[str, Any] | None) -> None:
        self._styles = styles if isinstance(styles, dict) else {}
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        full_rect = QRectF(self.rect())
        if full_rect.width() <= 0 or full_rect.height() <= 0:
            return

        radius = resolve_preload_window_radius_px({'widgets': [{'targets': ['Preload_Window'], 'styles': self._styles}]}, full_rect.width(), full_rect.height())
        background = self._styles.get('background') if isinstance(self._styles.get('background'), dict) else {}
        border = self._styles.get('border') if isinstance(self._styles.get('border'), dict) else {}

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(full_rect, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        brush = self._build_background_brush(full_rect, background)
        if brush is not None:
            painter.setBrush(brush)
        else:
            painter.setBrush(QBrush(self._fallback_background_color()))

        pen = self._build_border_pen(border)
        painter.setPen(pen)
        inset = pen.widthF() / 2.0 if pen.style() != Qt.PenStyle.NoPen else 0.0
        draw_rect = full_rect.adjusted(inset, inset, -inset, -inset)
        draw_radius = min(radius, min(draw_rect.width(), draw_rect.height()) / 2.0)
        painter.drawRoundedRect(draw_rect, draw_radius, draw_radius)

    def _build_background_brush(self, rect, background: dict[str, Any]) -> QBrush | None:
        gradient_value = background.get('gradient')
        if isinstance(gradient_value, dict):
            gradient = self._build_gradient_brush(rect, gradient_value)
            if gradient is not None:
                return QBrush(gradient)

        color_value = background.get('color')
        if isinstance(color_value, dict):
            gradient = self._build_gradient_brush(rect, color_value)
            if gradient is not None:
                return QBrush(gradient)
        elif isinstance(color_value, str):
            color = to_qcolor(color_value)
            if color is not None:
                return QBrush(color)
        return None

    def _fallback_background_color(self) -> QColor:
        color = self.palette().color(QPalette.ColorRole.Window)
        if color.isValid() and color.alpha() > 0:
            return color
        return QColor('#f2f2f2')

    def _build_gradient_brush(self, rect, value: dict[str, Any]) -> QLinearGradient | None:
        if str(value.get('type', 'linear')).strip().lower() != 'linear':
            return None
        direction = str(value.get('direction', 'vertical')).strip().lower()
        if direction == 'horizontal':
            gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        elif direction == 'diagonal':
            gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        elif direction == 'diagonal_reverse':
            gradient = QLinearGradient(rect.right(), rect.top(), rect.left(), rect.bottom())
        else:
            gradient = QLinearGradient(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())

        stops = value.get('stops') if isinstance(value.get('stops'), list) else []
        for stop in stops:
            if not isinstance(stop, (list, tuple)) or len(stop) != 2:
                continue
            try:
                pos = float(stop[0])
            except (TypeError, ValueError):
                continue
            color = to_qcolor(stop[1])
            if color is None:
                continue
            gradient.setColorAt(max(0.0, min(1.0, pos)), color)
        return gradient

    def _build_border_pen(self, border: dict[str, Any]) -> QPen:
        width = self._parse_px(border.get('width')) or 0.0
        color = to_qcolor(border.get('color'))
        style_name = str(border.get('style', 'solid')).strip().lower()
        if width <= 0.0 or style_name == 'none' or color is None:
            pen = QPen(Qt.PenStyle.NoPen)
            return pen

        style_map = {
            'solid': Qt.PenStyle.SolidLine,
            'dashed': Qt.PenStyle.DashLine,
            'dash': Qt.PenStyle.DashLine,
            'dotted': Qt.PenStyle.DotLine,
            'dot': Qt.PenStyle.DotLine,
            'dashdot': Qt.PenStyle.DashDotLine,
            'dash-dot': Qt.PenStyle.DashDotLine,
            'dashdotdot': Qt.PenStyle.DashDotDotLine,
            'dash-dot-dot': Qt.PenStyle.DashDotDotLine,
        }

        pen = QPen(color)
        pen.setStyle(style_map.get(style_name, Qt.PenStyle.SolidLine))
        pen.setWidthF(max(1.0, width))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen

    def _parse_px(self, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        if text.endswith('px'):
            text = text[:-2].strip()
        try:
            return float(text)
        except ValueError:
            return None
