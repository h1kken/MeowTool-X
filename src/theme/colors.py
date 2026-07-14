from __future__ import annotations

from typing import Any, Literal, cast, overload

from PySide6.QtGui import QColor


def to_qcolor(value: Any, *, fallback: QColor | None = None) -> QColor | None:
    if value is None:
        return fallback

    if isinstance(value, QColor):
        color = value

    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        color = QColor(text)

    elif isinstance(value, tuple):
        components = cast(tuple[object, ...], value)
        if len(components) not in (3, 4):
            return fallback
        try:
            color = QColor(*components)
        except TypeError:
            return fallback

    elif isinstance(value, list):
        components = cast(list[object], value)
        if len(components) not in (3, 4):
            return fallback
        try:
            color = QColor(*components)
        except TypeError:
            return fallback

    else:
        try:
            color = QColor(value)
        except TypeError:
            return fallback

    return color if color.isValid() else fallback


@overload
def normalize_color(value: Any, *, fallback_raw: Literal[False] = False) -> str | None: ...

@overload
def normalize_color(value: Any, *, fallback_raw: Literal[True]) -> str: ...

def normalize_color(value: Any, *, fallback_raw: bool = False) -> str | None:
    color = to_qcolor(value)
    if color is None:
        return str(value).strip() if fallback_raw else None

    if color.alpha() >= 255:
        return color.name()

    return f'rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})'
