from __future__ import annotations

import typing as t

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComboItem:
    tr_key: str
    text: str | None = None


type WidgetThemeMap = dict[str, object]
type PopupPlacement = t.Literal[
    'bottom-left',
    'bottom-right',
    'top-left',
    'top-right',
    'left-top',
    'left-bottom',
    'right-top',
    'right-bottom',
    'center',
    'cursor',
]


__all__ = (
    'PopupPlacement',
    'WidgetThemeMap',
)
