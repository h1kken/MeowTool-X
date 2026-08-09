from __future__ import annotations

import typing as t


def as_dict(value: object) -> dict[str, t.Any]:
    return t.cast(dict[str, t.Any], value) if isinstance(value, dict) else {}


def as_object_dict(value: object) -> dict[object, object] | None:
    return t.cast(dict[object, object], value) if isinstance(value, dict) else None


def coerce_int(value: object, default: int | None = None) -> int | None:
    try:
        return int(t.cast(t.Any, value))
    except (TypeError, ValueError):
        return default


def coerce_float(value: object, default: float | None = None) -> float | None:
    try:
        return float(t.cast(t.Any, value))
    except (TypeError, ValueError):
        return default


def coerce_number(value: object, default: float | None = None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return default

    text = value.strip().lower()
    if not text:
        return default
    if text.endswith('px'):
        text = text[:-2].strip()

    try:
        return float(text)
    except ValueError:
        return default


def coerce_box_sides(
    value: object,
    *,
    allow_negative: bool = False,
) -> tuple[float, float, float, float] | None:
    raw_values: list[object]
    if isinstance(value, (int, float)):
        raw_values = [value]
    elif isinstance(value, (list, tuple)):
        raw_values = list(t.cast(list[object] | tuple[object, ...], value))
    elif isinstance(value, str):
        raw_values = [part for part in value.replace(',', ' ').split() if part]
    else:
        return None

    if not raw_values or len(raw_values) > 4:
        return None

    numbers: list[float] = []
    for raw in raw_values:
        number = coerce_number(raw)
        if number is None:
            return None
        numbers.append(float(number) if allow_negative else max(0.0, float(number)))

    if len(numbers) == 1:
        top = right = bottom = left = numbers[0]
    elif len(numbers) == 2:
        top = bottom = numbers[0]
        right = left = numbers[1]
    elif len(numbers) == 3:
        top = numbers[0]
        right = left = numbers[1]
        bottom = numbers[2]
    else:
        top, right, bottom, left = numbers
    return top, right, bottom, left


__all__ = (
    'as_dict',
    'as_object_dict',
    'coerce_int',
    'coerce_float',
    'coerce_number',
    'coerce_box_sides',
)
