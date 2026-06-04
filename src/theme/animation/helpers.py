from __future__ import annotations

import math
from typing import Any, Callable

from PySide6.QtCore import QEasingCurve, Qt
from PySide6.QtGui import QColor

from src.utils.constants import GRADIENT_DIRECTIONS
from src.utils.regexes import CUBIC_BEZIER_PATTERN
from src.theme.colors import normalize_color, to_qcolor


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace('-', '_').replace(' ', '_')


def _to_color(value: Any) -> QColor | None:
    return to_qcolor(value)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_dash_border(data: Any) -> dict[str, Any] | None:
    default_dash = [4.0, 2.0]

    if isinstance(data, dict):
        provided: set[str] = set()
        if 'offset' in data or 'value' in data:
            provided.add('offset')
        if 'color' in data:
            provided.add('color')
        if 'opacity' in data:
            provided.add('opacity')
        if 'brightness' in data:
            provided.add('brightness')
        if 'saturation' in data:
            provided.add('saturation')
        if 'phase_offset' in data:
            provided.add('phase_offset')
        if any(key in data for key in ('phase_duration', 'rainbow_duration', 'period')):
            provided.add('phase_duration')
        if 'width' in data:
            provided.add('width')
        if 'radius' in data:
            provided.add('radius')
        if 'inset' in data:
            provided.add('inset')
        if 'dash' in data or 'dash_pattern' in data:
            provided.add('dash_pattern')
        if 'style' in data:
            provided.add('pen_style')
        if 'seamless' in data:
            provided.add('seamless')

        offset = _to_float(data.get('offset', data.get('value', 0.0)))
        color_raw = data.get('color', '#ffffff')
        shared_color = False
        color = _to_color(color_raw)
        opacity = _to_float(data.get('opacity', 1.0))
        brightness = _to_float(data.get('brightness', 1.0))
        saturation = _to_float(data.get('saturation', 1.0))
        phase_offset = _to_float(data.get('phase_offset', data.get('offset', 0.0)))
        phase_duration = _to_float(data.get('phase_duration', data.get('rainbow_duration', data.get('period', 5000))))
        width = _to_float(data.get('width', 1.0))
        radius = _to_float(data.get('radius', 6.0))
        inset = _to_float(data.get('inset', 0.5))

        dash_raw = data.get('dash', data.get('dash_pattern', default_dash))
        dash_pattern: list[float] = []
        if isinstance(dash_raw, (list, tuple)):
            for value in dash_raw:
                dash_value = _to_float(value)
                if dash_value is None:
                    continue
                dash_pattern.append(max(0.1, dash_value))

        pen_style = _parse_pen_style(data.get('style'), default=Qt.PenStyle.CustomDashLine)
        seamless = bool(data.get('seamless', True))

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
            'saturation': _clamp01(saturation if saturation is not None else 1.0),
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
        'saturation': 1.0,
        'width': 1.0,
        'radius': 6.0,
        'inset': 0.5,
        'dash_pattern': default_dash,
        'pen_style': Qt.PenStyle.CustomDashLine,
        'seamless': True,
        '_provided': {'offset'},
    }


def _normalize_gradient_border(data: Any) -> dict[str, Any] | None:
    default_stops = [
        (0.0, QColor('#ff8ac6')),
        (0.5, QColor('#8ac6ff')),
        (1.0, QColor('#ff8ac6')),
    ]

    if not isinstance(data, dict):
        return None

    phase_raw = data.get('phase', data.get('offset', data.get('value', 1.0)))
    shared_phase = False
    phase = _to_float(phase_raw)
    phase_offset = _to_float(data.get('phase_offset', data.get('offset', 0.0)))
    phase_duration = _to_float(data.get('phase_duration', data.get('rainbow_duration', data.get('period', 5000))))
    opacity = _to_float(data.get('opacity', 1.0))
    width = _to_float(data.get('width', 1.5))
    radius = _to_float(data.get('radius', 6.0))
    inset = _to_float(data.get('inset', 0.5))
    direction = str(data.get('direction', 'horizontal'))
    seamless = bool(data.get('seamless', True))
    pen_style = _parse_pen_style(data.get('style'), default=Qt.PenStyle.SolidLine)

    dash_raw = data.get('dash', data.get('dash_pattern', [4.0, 2.0]))
    dash_pattern: list[float] = []
    if isinstance(dash_raw, (list, tuple)):
        for value in dash_raw:
            dash_value = _to_float(value)
            if dash_value is None:
                continue
            dash_pattern.append(max(0.1, dash_value))

    stops_raw = data.get('stops')
    stops = _parse_gradient_stops(stops_raw) if stops_raw is not None else []
    if not stops:
        if (gradient_data := _normalize_gradient(data)) is not None:
            stops = gradient_data.get('stops', [])
    if not stops:
        stops = default_stops

    return {
        'phase': float(phase if phase is not None else 1.0),
        'phase_offset': float(phase_offset if phase_offset is not None else 0.0),
        'phase_duration': float(max(1.0, phase_duration if phase_duration is not None else 5000.0)),
        'shared_phase': bool(shared_phase),
        'opacity': _clamp01(opacity if opacity is not None else 1.0),
        'width': float(max(0.5, width if width is not None else 1.5)),
        'radius': float(max(0.0, radius if radius is not None else 6.0)),
        'inset': float(max(0.0, inset if inset is not None else 0.5)),
        'direction': direction,
        'seamless': seamless,
        'stops': [(_clamp01(pos), QColor(color)) for pos, color in stops],
        'pen_style': pen_style,
        'dash_pattern': dash_pattern or [4.0, 2.0],
    }


def _parse_gradient_stops(raw: Any) -> list[tuple[float, QColor]]:
    stops: list[tuple[float, QColor]] = []
    if not isinstance(raw, (list, tuple)):
        return stops

    for stop in raw:
        pos: Any = None
        color_raw: Any = None

        if isinstance(stop, dict):
            pos = stop.get('pos', stop.get('position'))
            color_raw = stop.get('color')
        elif isinstance(stop, (list, tuple)) and len(stop) >= 2:
            pos, color_raw = stop[0], stop[1]

        try:
            pos_f = float(pos)
        except (TypeError, ValueError):
            continue

        color = _to_color(color_raw)
        if color is None:
            continue

        stops.append((_clamp01(pos_f), color))

    return stops


def _parse_pen_style(raw: Any, *, default: Qt.PenStyle = Qt.PenStyle.CustomDashLine) -> Qt.PenStyle:
    if raw is None:
        return default

    token = _normalize_token(raw)
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


def _interpolate_color(start: QColor, end: QColor, t: float) -> QColor:
    t = _clamp01(t)
    return QColor(
        round(start.red() + (end.red() - start.red()) * t),
        round(start.green() + (end.green() - start.green()) * t),
        round(start.blue() + (end.blue() - start.blue()) * t),
        round(start.alpha() + (end.alpha() - start.alpha()) * t),
    )


def _normalize_gradient(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None

    stops_data = data.get('stops')
    if not isinstance(stops_data, list) or not stops_data:
        return None

    stops: list[tuple[float, QColor]] = []
    for stop in stops_data:
        pos: Any = None
        color_raw: Any = None

        if isinstance(stop, dict):
            pos = stop.get('pos', stop.get('position'))
            color_raw = stop.get('color')
        elif isinstance(stop, (list, tuple)) and len(stop) >= 2:
            pos, color_raw = stop[0], stop[1]

        try:
            pos_f = float(pos)
        except (TypeError, ValueError):
            continue

        color = _to_color(color_raw)
        if color is None:
            continue

        stops.append((_clamp01(pos_f), color))

    if not stops:
        return None

    g_type = _normalize_token(data.get('type', 'linear'))
    grad: dict[str, Any] = {
        'type': 'radial' if g_type == 'radial' else 'linear',
        'direction': str(data.get('direction', 'vertical')),
        'stops': stops,
    }

    if grad['type'] == 'radial':
        center = data.get('center', (0.5, 0.5))
        if isinstance(center, (list, tuple)) and len(center) >= 2:
            try:
                cx = float(center[0])
                cy = float(center[1])
            except (TypeError, ValueError):
                cx, cy = 0.5, 0.5
        else:
            cx, cy = 0.5, 0.5

        try:
            radius = float(data.get('radius', 0.5))
        except (TypeError, ValueError):
            radius = 0.5

        grad['center'] = (cx, cy)
        grad['radius'] = radius

    return grad


def _clone_gradient(grad: dict[str, Any]) -> dict[str, Any]:
    cloned = {
        'type': grad.get('type', 'linear'),
        'direction': grad.get('direction', 'vertical'),
        'stops': [(float(pos), QColor(color)) for pos, color in grad.get('stops', [])],
    }

    if cloned['type'] == 'radial':
        cloned['center'] = tuple(grad.get('center', (0.5, 0.5)))
        cloned['radius'] = float(grad.get('radius', 0.5))

    return cloned


def _interpolate_gradient(start: dict[str, Any], end: dict[str, Any], t: float) -> dict[str, Any]:
    t = _clamp01(t)

    s_stops = start.get('stops', [])
    e_stops = end.get('stops', [])
    if not s_stops or not e_stops:
        return _clone_gradient(end)

    count = max(len(s_stops), len(e_stops))
    new_stops: list[tuple[float, QColor]] = []

    for i in range(count):
        s_pos, s_color = s_stops[min(i, len(s_stops) - 1)]
        e_pos, e_color = e_stops[min(i, len(e_stops) - 1)]

        pos = s_pos + (e_pos - s_pos) * t
        color = _interpolate_color(s_color, e_color, t)
        new_stops.append((_clamp01(pos), color))

    result = {
        'type': end.get('type', start.get('type', 'linear')),
        'direction': end.get('direction', start.get('direction', 'vertical')),
        'stops': new_stops,
    }

    if result['type'] == 'radial':
        s_center = start.get('center', (0.5, 0.5))
        e_center = end.get('center', s_center)
        s_radius = float(start.get('radius', 0.5))
        e_radius = float(end.get('radius', s_radius))

        result['center'] = (
            float(s_center[0]) + (float(e_center[0]) - float(s_center[0])) * t,
            float(s_center[1]) + (float(e_center[1]) - float(s_center[1])) * t,
        )
        result['radius'] = s_radius + (e_radius - s_radius) * t

    return result


def _gradient_to_qss(grad: dict[str, Any]) -> str:
    stops = grad.get('stops', [])
    stop_parts = ', '.join(
        f'stop:{pos:.3f} {normalize_color(color)}'
        for pos, color in stops
        if normalize_color(color)
    )

    if grad.get('type') == 'radial':
        cx, cy = grad.get('center', (0.5, 0.5))
        radius = grad.get('radius', 0.5)
        return f'qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {stop_parts})'

    direction = grad.get('direction', 'vertical')
    x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(direction, (0, 0, 0, 1))
    return f'qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stop_parts})'


def _parse_easing(raw: Any) -> Callable[[float], float]:
    if isinstance(raw, dict):
        easing_type = _normalize_token(raw.get('type', raw.get('name', raw.get('curve', 'linear'))))

        if easing_type in ('bezier', 'cubic_bezier'):
            points = raw.get('points')
            if isinstance(points, (list, tuple)) and len(points) == 4:
                try:
                    x1, y1, x2, y2 = (float(points[0]), float(points[1]), float(points[2]), float(points[3]))
                    return _cubic_bezier_easing(x1, y1, x2, y2)
                except (TypeError, ValueError):
                    return _linear_easing

            try:
                x1 = float(raw.get('x1'))
                y1 = float(raw.get('y1'))
                x2 = float(raw.get('x2'))
                y2 = float(raw.get('y2'))
                return _cubic_bezier_easing(x1, y1, x2, y2)
            except (TypeError, ValueError):
                return _linear_easing

        if easing_type == 'steps':
            count = int(raw.get('count', 1) or 1)
            jump = _normalize_token(raw.get('jump', 'end'))
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

        return _qt_easing(_normalize_token(raw))

    return _linear_easing


def _parse_loop_count(raw: Any, *, default: int = 1) -> int:
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
        token = _normalize_token(raw)
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


