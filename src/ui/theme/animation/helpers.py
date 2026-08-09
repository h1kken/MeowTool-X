from __future__ import annotations

import math
import re
import typing as t

from PySide6.QtCore import QEasingCurve, Qt
from PySide6.QtGui import QColor

from src.utils.conversion import as_object_dict, coerce_int

_CUBIC_BEZIER_PATTERN = re.compile(
    r'cubic-bezier\s*\(([^)]+)\)',
    re.IGNORECASE,
)


def _iterable_data(value: t.Any) -> list[t.Any]:
    if isinstance(value, (list, tuple)):
        items = t.cast(list[t.Any] | tuple[t.Any, ...], value)
        return [item for item in items]
    return []


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_token(value: t.Any) -> str:
    return str(value).strip().lower().replace('-', '_').replace(' ', '_')


def _to_float(value: t.Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_dash_border(data: t.Any) -> dict[str, t.Any] | None:
    default_dash = [4.0, 2.0]

    if isinstance(data, dict):
        mapping = as_object_dict(t.cast(object, data)) or {}
        provided: set[str] = set()
        if 'offset' in mapping or 'value' in mapping:
            provided.add('offset')
        if 'color' in mapping:
            provided.add('color')
        if 'opacity' in mapping:
            provided.add('opacity')
        if 'width' in mapping:
            provided.add('width')
        if 'radius' in mapping:
            provided.add('radius')
        if 'inset' in mapping:
            provided.add('inset')
        if 'dash' in mapping or 'dash_pattern' in mapping:
            provided.add('dash_pattern')
        if 'style' in mapping:
            provided.add('pen_style')
        if 'seamless' in mapping:
            provided.add('seamless')

        offset = _to_float(mapping.get('offset', mapping.get('value', 0.0)))
        opacity = _to_float(mapping.get('opacity', 1.0))
        width = _to_float(mapping.get('width', 1.0))
        radius = _to_float(mapping.get('radius', 6.0))
        inset = _to_float(mapping.get('inset', 0.5))

        dash_raw = mapping.get('dash', mapping.get('dash_pattern', default_dash))
        dash_pattern: list[float] = []
        for value in _iterable_data(dash_raw):
            dash_value = _to_float(value)
            if dash_value is None:
                continue
            dash_pattern.append(max(0.1, dash_value))

        return {
            'offset': float(offset if offset is not None else 0.0),
            'color': QColor(str(mapping.get('color', '#ffffff'))),
            'opacity': _clamp01(opacity if opacity is not None else 1.0),
            'width': float(max(0.5, width if width is not None else 1.0)),
            'radius': float(max(0.0, radius if radius is not None else 6.0)),
            'inset': float(max(0.0, inset if inset is not None else 0.5)),
            'dash_pattern': dash_pattern or default_dash,
            'pen_style': _parse_pen_style(mapping.get('style'), default=Qt.PenStyle.CustomDashLine),
            'seamless': bool(mapping.get('seamless', True)),
            '_provided': provided,
        }

    offset = _to_float(data)
    if offset is None:
        return None

    return {
        'offset': float(offset),
        'color': QColor('#ffffff'),
        'opacity': 1.0,
        'width': 1.0,
        'radius': 6.0,
        'inset': 0.5,
        'dash_pattern': default_dash,
        'pen_style': Qt.PenStyle.CustomDashLine,
        'seamless': True,
        '_provided': {'offset'},
    }


def _parse_pen_style(raw: t.Any, *, default: Qt.PenStyle = Qt.PenStyle.CustomDashLine) -> Qt.PenStyle:
    if raw is None:
        return default

    token = normalize_token(raw)
    aliases: dict[str, Qt.PenStyle] = {
        'solid': Qt.PenStyle.SolidLine,
        'solidline': Qt.PenStyle.SolidLine,
        'dash': Qt.PenStyle.DashLine,
        'dashed': Qt.PenStyle.DashLine,
        'dashline': Qt.PenStyle.DashLine,
        'dot': Qt.PenStyle.DotLine,
        'dotted': Qt.PenStyle.DotLine,
        'dotline': Qt.PenStyle.DotLine,
        'dashdot': Qt.PenStyle.DashDotLine,
        'dash_dot': Qt.PenStyle.DashDotLine,
        'dashdotline': Qt.PenStyle.DashDotLine,
        'dashdotdot': Qt.PenStyle.DashDotDotLine,
        'dash_dot_dot': Qt.PenStyle.DashDotDotLine,
        'dashdotdotline': Qt.PenStyle.DashDotDotLine,
        'custom': Qt.PenStyle.CustomDashLine,
        'customdash': Qt.PenStyle.CustomDashLine,
        'custom_dash': Qt.PenStyle.CustomDashLine,
    }
    return aliases.get(token, default)


def interpolate_color(start: QColor, end: QColor, t: float) -> QColor:
    t = _clamp01(t)
    return QColor(
        round(start.red() + (end.red() - start.red()) * t),
        round(start.green() + (end.green() - start.green()) * t),
        round(start.blue() + (end.blue() - start.blue()) * t),
        round(start.alpha() + (end.alpha() - start.alpha()) * t),
    )


def parse_easing(raw: t.Any) -> t.Callable[[float], float]:
    if isinstance(raw, dict):
        mapping = as_object_dict(t.cast(object, raw)) or {}
        easing_type = normalize_token(mapping.get('type', mapping.get('name', mapping.get('curve', 'linear'))))

        if easing_type in ('bezier', 'cubic_bezier'):
            points = mapping.get('points')
            if isinstance(points, (list, tuple)):
                try:
                    point_items = _iterable_data(points)
                    if len(point_items) != 4:
                        return _linear_easing
                    x1 = float(point_items[0])
                    y1 = float(point_items[1])
                    x2 = float(point_items[2])
                    y2 = float(point_items[3])
                    return _cubic_bezier_easing(x1, y1, x2, y2)
                except (TypeError, ValueError):
                    return _linear_easing

            x1 = _to_float(mapping.get('x1'))
            y1 = _to_float(mapping.get('y1'))
            x2 = _to_float(mapping.get('x2'))
            y2 = _to_float(mapping.get('y2'))
            if x1 is None or y1 is None or x2 is None or y2 is None:
                return _linear_easing
            return _cubic_bezier_easing(x1, y1, x2, y2)

        if easing_type == 'steps':
            count = max(1, coerce_int(mapping.get('count', 1), 1) or 1)
            jump = normalize_token(mapping.get('jump', 'end'))
            return _steps_easing(count, jump)

        return _qt_easing(easing_type)

    if isinstance(raw, str):
        match = _CUBIC_BEZIER_PATTERN.search(raw)
        if match:
            parts = [p.strip() for p in match.group(1).split(',')]
            if len(parts) == 4:
                try:
                    x1, y1, x2, y2 = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                    return _cubic_bezier_easing(x1, y1, x2, y2)
                except ValueError:
                    return _linear_easing
        return _qt_easing(normalize_token(raw))

    return _linear_easing


def parse_loop_count(raw: t.Any, *, default: int = 1) -> int:
    if raw is None:
        return default

    if isinstance(raw, bool):
        return -1 if raw else default

    if isinstance(raw, (int, float)):
        try:
            return max(int(raw), 1)
        except (TypeError, ValueError):
            return default

    if isinstance(raw, str):
        token = normalize_token(raw)
        if token in {'true', 'infinite', 'forever', 'loop'}:
            return -1
        if token in {'false', 'none', 'once'}:
            return default
        try:
            return max(int(float(raw)), 1)
        except ValueError:
            return default

    return default


def _linear_easing(value: float) -> float:
    return _clamp01(value)


def _qt_easing(name: str) -> t.Callable[[float], float]:
    curve_map = {
        'linear': QEasingCurve.Type.Linear,
        'in_quad': QEasingCurve.Type.InQuad,
        'out_quad': QEasingCurve.Type.OutQuad,
        'in_out_quad': QEasingCurve.Type.InOutQuad,
        'in_cubic': QEasingCurve.Type.InCubic,
        'out_cubic': QEasingCurve.Type.OutCubic,
        'in_out_cubic': QEasingCurve.Type.InOutCubic,
        'in_quart': QEasingCurve.Type.InQuart,
        'out_quart': QEasingCurve.Type.OutQuart,
        'in_out_quart': QEasingCurve.Type.InOutQuart,
        'in_quint': QEasingCurve.Type.InQuint,
        'out_quint': QEasingCurve.Type.OutQuint,
        'in_out_quint': QEasingCurve.Type.InOutQuint,
        'in_sine': QEasingCurve.Type.InSine,
        'out_sine': QEasingCurve.Type.OutSine,
        'in_out_sine': QEasingCurve.Type.InOutSine,
        'in_expo': QEasingCurve.Type.InExpo,
        'out_expo': QEasingCurve.Type.OutExpo,
        'in_out_expo': QEasingCurve.Type.InOutExpo,
        'in_circ': QEasingCurve.Type.InCirc,
        'out_circ': QEasingCurve.Type.OutCirc,
        'in_out_circ': QEasingCurve.Type.InOutCirc,
        'in_back': QEasingCurve.Type.InBack,
        'out_back': QEasingCurve.Type.OutBack,
        'in_out_back': QEasingCurve.Type.InOutBack,
        'in_bounce': QEasingCurve.Type.InBounce,
        'out_bounce': QEasingCurve.Type.OutBounce,
        'in_out_bounce': QEasingCurve.Type.InOutBounce,
        'in_elastic': QEasingCurve.Type.InElastic,
        'out_elastic': QEasingCurve.Type.OutElastic,
        'in_out_elastic': QEasingCurve.Type.InOutElastic,
    }
    curve = QEasingCurve(curve_map.get(name, QEasingCurve.Type.Linear))
    return lambda value: _clamp01(curve.valueForProgress(_clamp01(value)))


def _cubic_bezier_easing(x1: float, y1: float, x2: float, y2: float) -> t.Callable[[float], float]:
    def sample_curve_x(t: float) -> float:
        return ((1.0 - 3.0 * x2 + 3.0 * x1) * t ** 3) + ((3.0 * x2 - 6.0 * x1) * t ** 2) + (3.0 * x1 * t)

    def sample_curve_y(t: float) -> float:
        return ((1.0 - 3.0 * y2 + 3.0 * y1) * t ** 3) + ((3.0 * y2 - 6.0 * y1) * t ** 2) + (3.0 * y1 * t)

    def sample_curve_derivative_x(t: float) -> float:
        return (3.0 * (1.0 - 3.0 * x2 + 3.0 * x1) * t ** 2) + (2.0 * (3.0 * x2 - 6.0 * x1) * t) + (3.0 * x1)

    def solve_curve_x(x: float, epsilon: float = 1e-6) -> float:
        t = x
        for _ in range(8):
            x_est = sample_curve_x(t) - x
            if abs(x_est) < epsilon:
                return t
            derivative = sample_curve_derivative_x(t)
            if abs(derivative) < epsilon:
                break
            t -= x_est / derivative

        t0 = 0.0
        t1 = 1.0
        t = x
        while t0 < t1:
            x_est = sample_curve_x(t)
            if abs(x_est - x) < epsilon:
                return t
            if x > x_est:
                t0 = t
            else:
                t1 = t
            t = (t0 + t1) / 2.0
            if abs(t1 - t0) < epsilon:
                break
        return t

    return lambda value: _clamp01(sample_curve_y(solve_curve_x(_clamp01(value))))


def _steps_easing(count: int, jump: str) -> t.Callable[[float], float]:
    count = max(1, int(count))
    jump_mode = jump if jump in {'start', 'end', 'both', 'none'} else 'end'

    def easing(value: float) -> float:
        progress = _clamp01(value)
        if jump_mode == 'start':
            result = math.ceil(progress * count) / count
        elif jump_mode == 'both':
            result = math.floor((progress * (count + 1)) + 1.0) / (count + 1)
        elif jump_mode == 'none':
            result = math.floor(progress * (count - 1)) / max(1, count - 1)
        else:
            result = math.floor(progress * count) / count
        return _clamp01(result)

    return easing
