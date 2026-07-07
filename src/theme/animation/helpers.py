from __future__ import annotations

import math
from typing import Any, Callable, cast

from PySide6.QtCore import QEasingCurve, Qt
from PySide6.QtGui import QColor

from src.theme.colors import normalize_color, to_qcolor
from src.theme.constants import GRADIENT_DIRECTIONS
from src.theme.regexes import CUBIC_BEZIER_PATTERN
from src.theme.schema.access import coerce_int, object_map

ColorStop = tuple[float, QColor]
GradientData = dict[str, Any]


def _iterable_data(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        items = cast(list[Any] | tuple[Any, ...], value)
        return [item for item in items]
    return []


def _color_stops(value: Any) -> list[ColorStop]:
    if not isinstance(value, list):
        return []

    items = cast(list[Any], value)
    result: list[ColorStop] = []
    for item in items:
        item_tuple = cast(tuple[Any, ...], item) if isinstance(item, tuple) else ()
        if (
            len(item_tuple) == 2
            and isinstance(item_tuple[0], (int, float))
            and isinstance(item_tuple[1], QColor)
        ):
            result.append((float(item_tuple[0]), QColor(item_tuple[1])))
    return result


def _point2(value: Any, default: tuple[float, float] = (0.5, 0.5)) -> tuple[float, float]:
    if isinstance(value, (list, tuple)):
        items = cast(list[Any] | tuple[Any, ...], value)
        if len(items) < 2:
            return default
        x = _to_float(items[0])
        y = _to_float(items[1])
        if x is not None and y is not None:
            return float(x), float(y)
    return default


def _float_or(value: Any, default: float) -> float:
    numeric = _to_float(value)
    return float(numeric) if numeric is not None else default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace('-', '_').replace(' ', '_')


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_dash_border(data: Any) -> dict[str, Any] | None:
    default_dash = [4.0, 2.0]

    if isinstance(data, dict):
        mapping = object_map(cast(object, data)) or {}
        provided: set[str] = set()
        if 'offset' in mapping or 'value' in mapping:
            provided.add('offset')
        if 'color' in mapping:
            provided.add('color')
        if 'opacity' in mapping:
            provided.add('opacity')
        if 'brightness' in mapping:
            provided.add('brightness')
        if 'phase_offset' in mapping:
            provided.add('phase_offset')
        if any(key in mapping for key in ('phase_duration', 'rainbow_duration', 'period')):
            provided.add('phase_duration')
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
        color_raw = mapping.get('color', '#ffffff')
        shared_color = False
        color = to_qcolor(color_raw)
        opacity = _to_float(mapping.get('opacity', 1.0))
        brightness = _to_float(mapping.get('brightness', 1.0))
        phase_offset = _to_float(mapping.get('phase_offset', mapping.get('offset', 0.0)))
        phase_duration = _to_float(mapping.get('phase_duration', mapping.get('rainbow_duration', mapping.get('period', 5000))))
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

        pen_style = _parse_pen_style(mapping.get('style'), default=Qt.PenStyle.CustomDashLine)
        seamless = bool(mapping.get('seamless', True))

        if color is None:
            color = QColor('#ffffff')

        return {
            'offset': float(offset if offset is not None else 0.0),
            'color': QColor(color),
            'shared_color': bool(shared_color),
            'phase_offset': float(phase_offset if phase_offset is not None else 0.0),
            'phase_duration': float(max(1.0, phase_duration if phase_duration is not None else 5000.0)),
            'opacity': _clamp01(opacity if opacity is not None else 1.0),
            'brightness': _clamp01(brightness if brightness is not None else 1.0),
            'width': float(max(0.5, width if width is not None else 1.0)),
            'radius': float(max(0.0, radius if radius is not None else 6.0)),
            'inset': float(max(0.0, inset if inset is not None else 0.5)),
            'dash_pattern': dash_pattern or default_dash,
            'pen_style': pen_style,
            'seamless': seamless,
            '_provided': provided,
        }

    offset = _to_float(data)
    if offset is None:
        return None

    return {
        'offset': float(offset),
        'color': QColor('#ffffff'),
        'shared_color': False,
        'phase_offset': 0.0,
        'phase_duration': 5000.0,
        'opacity': 1.0,
        'brightness': 1.0,
        'width': 1.0,
        'radius': 6.0,
        'inset': 0.5,
        'dash_pattern': default_dash,
        'pen_style': Qt.PenStyle.CustomDashLine,
        'seamless': True,
        '_provided': {'offset'},
    }
def _parse_gradient_stops(raw: Any) -> list[ColorStop]:
    stops: list[ColorStop] = []
    items = _iterable_data(raw)
    if not items:
        return stops

    for stop in items:
        pos: Any = None
        color_raw: Any = None

        if isinstance(stop, dict):
            stop_data = object_map(cast(object, stop)) or {}
            pos = stop_data.get('pos', stop_data.get('position'))
            color_raw = stop_data.get('color')
        elif isinstance(stop, (list, tuple)):
            stop_items = _iterable_data(stop)
            if len(stop_items) >= 2:
                pos, color_raw = stop_items[0], stop_items[1]

        try:
            pos_f = float(pos)
        except (TypeError, ValueError):
            continue

        color = to_qcolor(color_raw)
        if color is None:
            continue

        stops.append((_clamp01(pos_f), color))

    return stops


def _parse_pen_style(raw: Any, *, default: Qt.PenStyle = Qt.PenStyle.CustomDashLine) -> Qt.PenStyle:
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


def normalize_gradient(data: Any) -> GradientData | None:
    mapping = object_map(data)
    if mapping is None:
        return None

    stops = _parse_gradient_stops(mapping.get('stops'))
    if not stops:
        return None

    g_type = normalize_token(mapping.get('type', 'linear'))
    grad: GradientData = {
        'type': 'radial' if g_type == 'radial' else 'linear',
        'direction': str(mapping.get('direction', 'vertical')),
        'stops': stops,
    }

    if grad['type'] == 'radial':
        cx, cy = _point2(mapping.get('center', (0.5, 0.5)))
        radius = _float_or(mapping.get('radius', 0.5), 0.5)

        grad['center'] = (cx, cy)
        grad['radius'] = radius

    return grad


def clone_gradient(grad: GradientData) -> GradientData:
    stops = _color_stops(grad.get('stops', []))
    cloned = {
        'type': grad.get('type', 'linear'),
        'direction': grad.get('direction', 'vertical'),
        'stops': [(pos, QColor(color)) for pos, color in stops],
    }

    if cloned['type'] == 'radial':
        cloned['center'] = _point2(grad.get('center', (0.5, 0.5)))
        cloned['radius'] = _float_or(grad.get('radius', 0.5), 0.5)

    return cloned


def interpolate_gradient(start: GradientData, end: GradientData, t: float) -> GradientData:
    t = _clamp01(t)

    s_stops = _color_stops(start.get('stops', []))
    e_stops = _color_stops(end.get('stops', []))
    if not s_stops or not e_stops:
        return clone_gradient(end)

    count = max(len(s_stops), len(e_stops))
    new_stops: list[ColorStop] = []

    for i in range(count):
        s_pos, s_color = s_stops[min(i, len(s_stops) - 1)]
        e_pos, e_color = e_stops[min(i, len(e_stops) - 1)]

        pos = s_pos + (e_pos - s_pos) * t
        color = interpolate_color(s_color, e_color, t)
        new_stops.append((_clamp01(pos), color))

    result = {
        'type': end.get('type', start.get('type', 'linear')),
        'direction': end.get('direction', start.get('direction', 'vertical')),
        'stops': new_stops,
    }

    if result['type'] == 'radial':
        s_center = _point2(start.get('center', (0.5, 0.5)))
        e_center = _point2(end.get('center', s_center), s_center)
        s_radius = _float_or(start.get('radius', 0.5), 0.5)
        e_radius = _float_or(end.get('radius', s_radius), s_radius)

        result['center'] = (
            float(s_center[0]) + (float(e_center[0]) - float(s_center[0])) * t,
            float(s_center[1]) + (float(e_center[1]) - float(s_center[1])) * t,
        )
        result['radius'] = s_radius + (e_radius - s_radius) * t

    return result


def gradient_to_qss(grad: GradientData) -> str:
    stops = _color_stops(grad.get('stops', []))
    stop_parts = ', '.join(
        f'stop:{pos:.3f} {normalize_color(color)}'
        for pos, color in stops
        if normalize_color(color)
    )

    if grad.get('type') == 'radial':
        cx, cy = _point2(grad.get('center', (0.5, 0.5)))
        radius = _float_or(grad.get('radius', 0.5), 0.5)
        return f'qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {stop_parts})'

    direction = grad.get('direction', 'vertical')
    x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(direction, (0, 0, 0, 1))
    return f'qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stop_parts})'


def parse_easing(raw: Any) -> Callable[[float], float]:
    if isinstance(raw, dict):
        mapping = object_map(cast(object, raw)) or {}
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
        match = CUBIC_BEZIER_PATTERN.search(raw)
        if match:
            parts = [p.strip() for p in match.group(1).split(',')]
            if len(parts) == 4:
                try:
                    x1, y1, x2, y2 = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                    return _cubic_bezier_easing(x1, y1, x2, y2)
                except (TypeError, ValueError):
                    return _linear_easing

        return _qt_easing(normalize_token(raw))

    return _linear_easing


def parse_loop_count(raw: Any, *, default: int = 1) -> int:
    if raw is None:
        return default

    if isinstance(raw, bool):
        return -1 if raw else 1

    if isinstance(raw, (int, float)):
        count = int(raw)
        if count < 0:
            return -1
        return max(1, count)

    if isinstance(raw, str):
        token = normalize_token(raw)
        if token in ('infinite', 'forever', 'always', 'loop', 'endless'):
            return -1
        if token in ('once', 'one', 'single'):
            return 1

        numeric = _to_float(token)
        if numeric is not None:
            count = int(numeric)
            if count < 0:
                return -1
            return max(1, count)

    return default


def _qt_easing(name: str) -> Callable[[float], float]:
    aliases = {
        'linear': 'Linear',
        'in_quad': 'InQuad',
        'out_quad': 'OutQuad',
        'in_out_quad': 'InOutQuad',
        'in_cubic': 'InCubic',
        'out_cubic': 'OutCubic',
        'in_out_cubic': 'InOutCubic',
        'in_quart': 'InQuart',
        'out_quart': 'OutQuart',
        'in_out_quart': 'InOutQuart',
        'in_quint': 'InQuint',
        'out_quint': 'OutQuint',
        'in_out_quint': 'InOutQuint',
        'in_sine': 'InSine',
        'out_sine': 'OutSine',
        'in_out_sine': 'InOutSine',
        'in_expo': 'InExpo',
        'out_expo': 'OutExpo',
        'in_out_expo': 'InOutExpo',
        'in_circ': 'InCirc',
        'out_circ': 'OutCirc',
        'in_out_circ': 'InOutCirc',
        'in_back': 'InBack',
        'out_back': 'OutBack',
        'in_out_back': 'InOutBack',
        'in_bounce': 'InBounce',
        'out_bounce': 'OutBounce',
        'in_out_bounce': 'InOutBounce',
        'in_elastic': 'InElastic',
        'out_elastic': 'OutElastic',
        'in_out_elastic': 'InOutElastic',
    }

    enum_name = aliases.get(name, 'Linear')
    qt_type = getattr(QEasingCurve.Type, enum_name, QEasingCurve.Type.Linear)
    curve = QEasingCurve(qt_type)
    return lambda t, c=curve: c.valueForProgress(_clamp01(t))


def _linear_easing(t: float) -> float:
    return _clamp01(t)


def _steps_easing(count: int, jump: str) -> Callable[[float], float]:
    steps = max(1, int(count))

    if jump in ('start', 'jump_start'):
        return lambda t: _clamp01((math.floor(_clamp01(t) * steps) + 1) / steps)

    if jump in ('none', 'jump_none'):
        return lambda t: _clamp01((math.floor(_clamp01(t) * (steps - 1)) + 0.5) / steps)

    return lambda t: _clamp01(math.floor(_clamp01(t) * steps) / steps)


def _cubic_bezier_easing(x1: float, y1: float, x2: float, y2: float) -> Callable[[float], float]:
    x1 = _clamp01(x1)
    x2 = _clamp01(x2)

    def sample(u: float, p1: float, p2: float) -> float:
        inv = 1.0 - u
        return (3.0 * inv ** 2 * u * p1) + (3.0 * inv * u ** 2 * p2) + (u ** 3)

    def easing(t: float) -> float:
        target = _clamp01(t)
        lo, hi = 0.0, 1.0
        for _ in range(22):
            mid = (lo + hi) / 2.0
            x = sample(mid, x1, x2)
            if x < target:
                lo = mid
            else:
                hi = mid

        u = (lo + hi) / 2.0
        return _clamp01(sample(u, y1, y2))

    return easing




