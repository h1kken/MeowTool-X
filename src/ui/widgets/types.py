from __future__ import annotations

import typing as t


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
