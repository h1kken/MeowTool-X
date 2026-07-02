from __future__ import annotations

from typing import Literal

type WidgetThemeMap = dict[str, object]
type PopupPlacement = Literal[
    "bottom-left",
    "bottom-right",
    "top-left",
    "top-right",
    "left-top",
    "left-bottom",
    "right-top",
    "right-bottom",
    "center",
    "cursor",
]

__all__ = ("PopupPlacement", "WidgetThemeMap")
