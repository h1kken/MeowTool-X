from __future__ import annotations

from typing import Any, Literal, overload

from PySide6.QtGui import QColor


def to_qcolor(value: Any) -> QColor | None:
    if value is None:
        return None

    if isinstance(value, QColor):
        color = QColor(value)
        return color if color.isValid() else None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        color = QColor(text)
        return color if color.isValid() else None

    try:
        color = QColor(value)
    except TypeError:
        return None
    return color if color.isValid() else None


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
