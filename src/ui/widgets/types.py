from __future__ import annotations

import typing as t

from dataclasses import dataclass

from src.translation import TranslationKey as TrKey


@dataclass(frozen=True, slots=True)
class ComboItem:
    tr: TrKey = TrKey()
    text: str | None = None


type WidgetDataMap = dict[str, object]
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
    'WidgetDataMap',
)
