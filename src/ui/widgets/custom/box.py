from __future__ import annotations

from copy import deepcopy
import re
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from src.theme.gradients import build_background_brush, normalize_gradient_data
from src.theme.schema.access import coerce_number, theme_map
from src.theme.schema.types import ThemeMap


ThemeState = ThemeMap
_BOX_BORDER_SIDES = ('top', 'right', 'bottom', 'left')

if TYPE_CHECKING:
    class _BoxThemeBase:
        def setAttribute(self, attr: Qt.WidgetAttribute, on: bool = True) -> None: ...
        def update(self, *args: object) -> None: ...
        def rect(self) -> QRect: ...
else:
    class _BoxThemeBase:
        pass

class BoxThemeMixin(_BoxThemeBase):
    def init_box_theme(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._box_theme: ThemeState | None = None

    def apply_box_theme(self, theme: ThemeState) -> None:
        background = theme_map(theme.get('background')) or {}
        border = theme_map(theme.get('border')) or {}
        self._box_theme = {
            'background': self._normalize_background(background),
            'border': self._normalize_border(border),
            'radius': self._resolve_radius_source(background, border),
        }
        self.update()

    def clear_box_theme(self) -> None:
        self._box_theme = None
        self.update()

    def has_box_theme(self) -> bool:
        return theme_map(getattr(self, '_box_theme', None)) is not None

    def box_theme_state(self) -> ThemeState | None:
        theme = theme_map(getattr(self, '_box_theme', None))
        return deepcopy(theme) if theme is not None else None

    def restore_box_theme_state(self, state: ThemeState | None) -> None:
        self._box_theme = deepcopy(state) if state is not None else None
        self.update()

    def set_box_background_color(self, value: Any) -> bool:
        color = self._theme_color(value)
        if color is None:
            return False
        theme = self._ensure_box_theme()
        theme['background'] = {'color': color, 'gradient': None}
        self.update()
        return True

    def set_box_border_color(self, value: Any) -> bool:
        color = self._theme_color(value)
        if color is None:
            return False
        theme = self._ensure_box_theme()
        border = cast(ThemeState, theme.setdefault('border', self._normalize_border({})))
        border['color'] = color
        for side_data in self._configured_side_borders(border):
            side_data['color'] = QColor(color)
        self.update()
        return True

    def set_box_border(
        self,
        *,
        color: Any | None = None,
        gradient: Any | None = None,
        width: Any | None = None,
        radius: Any | None = None,
        style: str | None = None,
    ) -> bool:
        theme = self._ensure_box_theme()
        border = cast(ThemeState, theme.setdefault('border', self._normalize_border({})))

        if color is not None:
            border_color = self._theme_color(color)
            if border_color is None:
                return False
            border['color'] = border_color
            border['gradient'] = None
            for side_data in self._configured_side_borders(border):
                side_data['color'] = QColor(border_color)
                side_data['gradient'] = None

        if gradient is not None:
            border_gradient = normalize_gradient_data(gradient)
            if not isinstance(border_gradient, dict):
                return False
            border['gradient'] = border_gradient
            border['color'] = None
            for side_data in self._configured_side_borders(border):
                side_data['gradient'] = deepcopy(border_gradient)
                side_data['color'] = None

        if width is not None:
            border['width'] = max(0.0, self._theme_measure(width, default=0.0))
        if radius is not None:
            theme['radius'] = radius
        if isinstance(style, str) and style.strip():
            border['style'] = style.strip().lower()

        self.update()
        return True

    def draw_box_theme(self, painter: QPainter, rect: QRectF | None = None) -> None:
        theme = theme_map(getattr(self, '_box_theme', None))
        if theme is None:
            return

        border = theme_map(theme.get('border')) or {}
        max_border_width = self._max_border_width(border)
        rect = QRectF(rect if rect is not None else self.rect()).adjusted(
            max_border_width / 2.0,
            max_border_width / 2.0,
            -max_border_width / 2.0,
            -max_border_width / 2.0,
        )
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return

        radius = self._radius(theme.get('radius'), rect)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        background = theme_map(theme.get('background')) or {}
        self._draw_background(painter, path, rect, background)
        self._draw_border(painter, path, rect, border)

    def _ensure_box_theme(self) -> ThemeState:
        theme = theme_map(getattr(self, '_box_theme', None))
        if theme is None:
            self._box_theme = {
                'background': self._normalize_background({}),
                'border': self._normalize_border({}),
                'radius': 0.0,
            }
            theme = self._box_theme
        return theme

    def _normalize_background(self, data: Any) -> ThemeState:
        mapping = theme_map(data) or {}

        gradient = theme_map(mapping.get('gradient'))
        if gradient is None:
            gradient = theme_map(mapping.get('color'))

        return {
            'color': self._theme_color(mapping.get('color')) if theme_map(mapping.get('color')) is None else None,
            'gradient': normalize_gradient_data(gradient) if isinstance(gradient, dict) else None,
        }

    def _normalize_border(self, data: Any) -> ThemeState:
        mapping = theme_map(data) or {}
        border_gradient = theme_map(mapping.get('gradient'))
        full = {
            'color': self._theme_color(mapping.get('color')),
            'gradient': normalize_gradient_data(border_gradient) if border_gradient is not None else None,
            'width': self._theme_measure(mapping.get('width'), default=0.0),
            'style': str(mapping.get('style', 'solid') or 'solid').strip().lower(),
        }
        for side in _BOX_BORDER_SIDES:
            side_data = self._normalize_side_border(mapping.get(side))
            side_gradient = theme_map(side_data.get('gradient', mapping.get(f'{side}_gradient')))
            full[side] = {
                'color': self._theme_color(side_data.get('color', mapping.get(f'{side}_color'))),
                'gradient': normalize_gradient_data(side_gradient) if side_gradient is not None else None,
                'width': self._theme_measure(
                    side_data.get('width', mapping.get(f'{side}_width')),
                    default=-1.0,
                ),
                'style': str(side_data.get('style', mapping.get(f'{side}_style', ''))).strip().lower(),
            }
        return full

    def _normalize_side_border(self, value: Any) -> ThemeState:
        mapping = theme_map(value)
        if mapping is not None:
            return mapping
        if not isinstance(value, str):
            return {}

        text = value.strip().rstrip(';').strip()
        if ':' in text:
            text = text.split(':', 1)[1].strip()
        match = re.match(r'^(\S+)\s+(\S+)\s+(.+)$', text)
        if not match:
            return {}
        return {
            'width': match.group(1),
            'style': match.group(2),
            'color': match.group(3).strip(),
        }

    def _resolve_radius_source(self, background: Any, border: Any) -> Any:
        background_mapping = theme_map(background) or {}
        border_mapping = theme_map(border) or {}
        return border_mapping.get('radius', background_mapping.get('radius', 0.0))

    def _draw_background(self, painter: QPainter, path: QPainterPath, rect: QRectF, background: dict[str, Any]) -> None:
        painter.save()
        brush = build_background_brush(rect, {'gradient': background.get('gradient')})
        if brush is None:
            color = background.get('color')
            if isinstance(color, QColor) and color.isValid():
                painter.fillPath(path, color)
        else:
            painter.fillPath(path, brush)
        painter.restore()

    def _draw_border(self, painter: QPainter, path: QPainterPath, rect: QRectF, border: dict[str, Any]) -> None:
        width = max(0.0, float(border.get('width', 0.0) or 0.0))
        color = border.get('color')
        gradient = border.get('gradient')
        style = self._pen_style(border.get('style', 'solid'))
        brush = self._border_brush(rect, color=color, gradient=gradient)
        if width > 0.0 and brush is not None and style != Qt.PenStyle.NoPen:
            painter.save()
            pen = QPen(brush, width)
            pen.setStyle(style)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            painter.restore()

        self._draw_side_borders(painter, rect, border)

    def _draw_side_borders(self, painter: QPainter, rect: QRectF, border: dict[str, Any]) -> None:
        for side in _BOX_BORDER_SIDES:
            side_data = self._side_border_data(border, side)
            if side_data is None:
                continue

            width = float(side_data.get('width', -1.0) or -1.0)
            if width < 0.0:
                continue

            color = side_data.get('color') or border.get('color')
            gradient = side_data.get('gradient') or border.get('gradient')
            style = self._pen_style(side_data.get('style') or border.get('style', 'solid'))
            brush = self._border_brush(rect, color=color, gradient=gradient)
            if width <= 0.0 or brush is None or style == Qt.PenStyle.NoPen:
                continue

            painter.save()
            pen = QPen(brush, width)
            pen.setStyle(style)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            half = width / 2.0
            match side:
                case 'top':
                    painter.drawLine(QPointF(rect.left(), rect.top() + half), QPointF(rect.right(), rect.top() + half))
                case 'right':
                    painter.drawLine(QPointF(rect.right() - half, rect.top()), QPointF(rect.right() - half, rect.bottom()))
                case 'bottom':
                    painter.drawLine(QPointF(rect.left(), rect.bottom() - half), QPointF(rect.right(), rect.bottom() - half))
                case 'left':
                    painter.drawLine(QPointF(rect.left() + half, rect.top()), QPointF(rect.left() + half, rect.bottom()))
            painter.restore()

    def _max_border_width(self, border: dict[str, Any]) -> float:
        values = [self._theme_measure(border.get('width'), default=0.0)]
        for side in _BOX_BORDER_SIDES:
            side_data = self._side_border_data(border, side)
            if side_data is not None:
                values.append(max(0.0, float(side_data.get('width', -1.0) or -1.0)))
        return max(values or [0.0])

    def _side_has_any_border_value(self, side_data: dict[str, Any]) -> bool:
        return any(side_data.get(key) not in (None, '', -1.0) for key in ('color', 'gradient', 'width', 'style'))

    def _side_border_data(self, border: dict[str, Any], side: str) -> ThemeState | None:
        return theme_map(border.get(side))

    def _configured_side_borders(self, border: dict[str, Any]) -> list[ThemeState]:
        result: list[ThemeState] = []
        for side in _BOX_BORDER_SIDES:
            side_data = self._side_border_data(border, side)
            if side_data is not None and self._side_has_any_border_value(side_data):
                result.append(side_data)
        return result

    def _border_brush(self, rect: QRectF, *, color: Any, gradient: Any) -> QBrush | None:
        gradient_map = theme_map(gradient)
        if gradient_map is not None:
            brush = build_background_brush(rect, {'gradient': gradient_map})
            if isinstance(brush, QBrush):
                return brush
        if self._valid_color(color):
            return QBrush(color)
        return None

    def _radius(self, value: Any, rect: QRectF) -> float:
        base = max(0.0, min(rect.width(), rect.height()) / 2.0)
        if isinstance(value, str) and value.strip().endswith('%'):
            try:
                return max(0.0, min(base, min(rect.width(), rect.height()) * float(value.strip()[:-1]) / 100.0))
            except ValueError:
                return 0.0
        return max(0.0, min(base, self._theme_measure(value, default=0.0)))

    def _theme_measure(self, value: Any, *, default: float = 0.0) -> float:
        if isinstance(value, bool) or value is None:
            return default
        return float(coerce_number(value, default) or default)

    def _theme_color(self, value: Any) -> QColor | None:
        color = QColor(value)
        return QColor(color) if color.isValid() else None

    def _valid_color(self, color: Any) -> bool:
        return isinstance(color, QColor) and color.isValid() and color.alpha() > 0

    def _pen_style(self, value: object) -> Qt.PenStyle:
        match str(value or 'solid').strip().lower().replace('_', '-'):
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
