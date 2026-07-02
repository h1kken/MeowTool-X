from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor


def to_qcolor(value: Any, *, fallback: QColor | None = None) -> QColor | None:
    if value is None:
        return fallback

    if isinstance(value, QColor):
        color = value

    elif isinstance(value, str):
        color = QColor(value.strip())

    elif isinstance(value, (tuple, list)):
        if len(value) in (3, 4): # type: ignore
            color = QColor(*value)
        else:
            return fallback

    else:
        color = QColor(value)

    return color if color.isValid() else fallback


def normalize_color(value: Any, *, fallback_raw: bool = False) -> str | None:
    color = to_qcolor(value)
    if color is None:
        return str(value).strip() if fallback_raw else None

    if color.alpha() >= 255:
        return color.name()

    return f'rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})'