from __future__ import annotations

from copy import deepcopy
from math import cos, radians, sin
from collections.abc import Sequence
from typing import Any, TypeAlias, cast

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QGradient, QLinearGradient, QRadialGradient

from src.theme.colors import normalize_color, to_qcolor
from src.theme.constants import GRADIENT_DIRECTIONS

GradientMap: TypeAlias = dict[str, Any]
GradientStop: TypeAlias = tuple[float, QColor]
PointPair: TypeAlias = tuple[float, float]


def clone_gradient_data(data: object) -> GradientMap | None:
    if not isinstance(data, dict):
        return None
    gradient_data: GradientMap = cast(GradientMap, data)
    return deepcopy(gradient_data)


def clamp_unit_float(value: Any, default: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return max(0.0, min(1.0, numeric))


def adjust_qcolor(
    color: QColor,
    *,
    brightness: float = 1.0,
    saturation: float = 1.0,
) -> QColor:
    if not color.isValid():
        return QColor()

    result = QColor(color)
    saturation = clamp_unit_float(saturation)
    if saturation < 0.999:
        gray = round(
            (result.red() * 0.299)
            + (result.green() * 0.587)
            + (result.blue() * 0.114)
        )
        result = QColor(
            round(gray + (result.red() - gray) * saturation),
            round(gray + (result.green() - gray) * saturation),
            round(gray + (result.blue() - gray) * saturation),
            result.alpha(),
        )

    brightness = clamp_unit_float(brightness)
    if brightness >= 0.999:
        return result

    return QColor(
        round(result.red() * brightness),
        round(result.green() * brightness),
        round(result.blue() * brightness),
        result.alpha(),
    )


def adjust_gradient_data(
    data: Any,
    *,
    brightness: float = 1.0,
    saturation: float = 1.0,
) -> GradientMap | None:
    gradient = normalize_gradient_data(data)
    if gradient is None:
        return None

    adjusted = deepcopy(gradient)
    adjusted["stops"] = [
        [float(pos), adjust_qcolor(color, brightness=brightness, saturation=saturation)]
        for pos, color in parse_gradient_stops(gradient.get("stops"))
    ]
    return adjusted


def parse_gradient_stops(data: Any) -> list[GradientStop]:
    if not isinstance(data, (list, tuple)):
        return []

    stops: list[GradientStop] = []
    stops_source = cast(Sequence[Any], data)
    for stop in stops_source:
        pos: object | None = None
        color_value: object | None = None

        if isinstance(stop, dict):
            stop_map = cast(GradientMap, stop)
            pos = stop_map.get("pos", stop_map.get("position"))
            color_value = stop_map.get("color")
        elif isinstance(stop, (list, tuple)):
            pair = cast(Sequence[Any], stop)
            if len(pair) < 2:
                continue
            pos = pair[0]
            color_value = pair[1]
        else:
            continue

        if pos is None or color_value is None:
            continue

        pos_value = clamp_unit_float(pos, 0.0)

        color = to_qcolor(color_value)
        if color is None:
            continue

        stops.append((max(0.0, min(1.0, pos_value)), color))

    return stops


def normalize_gradient_data(data: Any) -> GradientMap | None:
    if not isinstance(data, dict):
        return None

    gradient_data = cast(GradientMap, data)
    stops = parse_gradient_stops(gradient_data.get("stops"))
    if not stops:
        return None

    normalized = deepcopy(gradient_data)
    normalized["stops"] = [[float(pos), QColor(color)] for pos, color in stops]
    return normalized


def _center_pair(value: Any) -> PointPair:
    if not isinstance(value, (list, tuple)):
        return 0.5, 0.5
    values = cast(list[Any] | tuple[Any, ...], value)
    if len(values) < 2:
        return 0.5, 0.5
    try:
        return float(values[0]), float(values[1])
    except (TypeError, ValueError):
        return 0.5, 0.5


def build_gradient_qss(data: Any) -> str | None:
    gradient = normalize_gradient_data(data)
    if gradient is None:
        return None

    stops = cast(list[GradientStop], gradient.get("stops", []))
    stop_parts = ", ".join(
        f"stop:{float(pos)} {normalize_color(color)}"
        for pos, color in stops
        if normalize_color(color)
    )

    gradient_type = str(gradient.get("type", "linear")).strip().lower() or "linear"
    if gradient_type == "radial":
        cx, cy = _center_pair(gradient.get("center", [0.5, 0.5]))
        try:
            radius = float(gradient.get("radius", 0.5))
        except (TypeError, ValueError):
            radius = 0.5
        return f"qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {stop_parts})"

    direction = (
        str(gradient.get("direction", "vertical")).strip().lower() or "vertical"
    )
    x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(direction, (0, 0, 0, 1))
    return f"qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stop_parts})"


def build_background_qss_rule(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None

    background_data = cast(GradientMap, data)
    gradient = (
        background_data.get("gradient")
        if isinstance(background_data.get("gradient"), dict)
        else None
    )
    if gradient is None and isinstance(background_data.get("color"), dict):
        gradient = background_data.get("color")

    if isinstance(gradient, dict) and (gradient_qss := build_gradient_qss(gradient)):
        return f"background: {gradient_qss};"

    color = background_data.get("color")
    if isinstance(color, str) and color.strip():
        return f"background-color: {normalize_color(color, fallback_raw=True)};"

    return None


def build_background_brush(rect: QRectF, data: Any) -> QBrush | None:
    if not isinstance(data, dict):
        return None

    background_data = cast(GradientMap, data)
    gradient_source = (
        background_data.get("gradient")
        if isinstance(background_data.get("gradient"), dict)
        else None
    )
    if gradient_source is None and isinstance(background_data.get("color"), dict):
        gradient_source = background_data.get("color")

    if isinstance(gradient_source, dict):
        brush = build_gradient_brush(rect, gradient_source)
        if brush is not None:
            return brush

    color = to_qcolor(background_data.get("color"))
    if color is not None:
        return QBrush(color)

    return None


def build_gradient_brush(rect: QRectF, data: Any) -> QBrush | None:
    gradient = normalize_gradient_data(data)
    if gradient is None:
        return None

    gradient_type = str(gradient.get("type", "linear")).strip().lower() or "linear"
    if gradient_type == "radial":
        cx, cy = _center_pair(gradient.get("center", [0.5, 0.5]))
        try:
            radius_factor = float(gradient.get("radius", 0.5))
        except (TypeError, ValueError):
            radius_factor = 0.5

        center_x = rect.left() + (rect.width() * cx)
        center_y = rect.top() + (rect.height() * cy)
        radius = max(1.0, min(rect.width(), rect.height()) * radius_factor)
        brush_gradient: QGradient = QRadialGradient(center_x, center_y, radius)
    else:
        angle = gradient.get("angle")
        if isinstance(angle, (int, float)):
            x1n, y1n, x2n, y2n = _gradient_points_from_angle(float(angle))
        else:
            direction = (
                str(gradient.get("direction", "vertical")).strip().lower()
                or "vertical"
            )
            x1n, y1n, x2n, y2n = GRADIENT_DIRECTIONS.get(direction, (0, 0, 0, 1))
        brush_gradient = QLinearGradient(
            rect.left() + (rect.width() * x1n),
            rect.top() + (rect.height() * y1n),
            rect.left() + (rect.width() * x2n),
            rect.top() + (rect.height() * y2n),
        )

    for stop in cast(list[list[Any]], gradient.get("stops", [])):
        if len(stop) < 2:
            continue
        pos = stop[0]
        color_value = stop[1]
        color = to_qcolor(color_value)
        if color is None:
            continue
        try:
            pos_value = float(pos)
        except (TypeError, ValueError):
            continue
        brush_gradient.setColorAt(max(0.0, min(1.0, pos_value)), color)

    return QBrush(brush_gradient)


def _gradient_points_from_angle(angle_degrees: float) -> tuple[float, float, float, float]:
    angle = radians(float(angle_degrees) % 360.0)
    dx = cos(angle) * 0.5
    dy = sin(angle) * 0.5
    center_x = 0.5
    center_y = 0.5
    return (
        center_x - dx,
        center_y - dy,
        center_x + dx,
        center_y + dy,
    )
