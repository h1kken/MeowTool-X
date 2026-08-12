from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QLayout, QWidget

from .constants import ALIGNMENT_FLAGS
from .helpers import parse_box_values, to_int

if t.TYPE_CHECKING:
    from src.core.types import DataMap
    from .types import QTHandler


# margin
def _apply_margin(target: QObject, styles: DataMap, *, store: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, QLayout):
        return
    
    margin = styles.get('margin')
    if isinstance(margin, str):
        margin = margin.split()

    if not isinstance(margin, list):
        return

    top, right, bottom, left = parse_box_values(styles, property_name='margin')
    target.setContentsMargins(left, top, right, bottom)
    
    if store is not None:
        store[target].add('margin')


# spacing
def _apply_spacing(target: QObject, styles: DataMap, *, store: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, QLayout):
        return
    
    spacing = to_int(styles.get('spacing'))
    if spacing is None:
        target.setSpacing(0)
        return
    
    target.setSpacing(spacing)
    
    if store is not None:
        store[target].add('spacing')


# align
def _apply_alignment(target: QObject, styles: DataMap, *, store: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, (QLayout, QWidget)):
        return
    
    setter = getattr(target, 'setAlignment', None)
    if not callable(setter):
        return
    
    result = Qt.AlignmentFlag(0)
    
    value = styles.get('alignment')
    
    match value:
        
        case str():
            alignment = ALIGNMENT_FLAGS.get(value.strip().lower())
            if alignment is not None:
                result |= alignment

        case list():
            for item in value:
                if not isinstance(item, str):
                    setter(Qt.AlignmentFlag(0))
                    return
                    
                alignment = ALIGNMENT_FLAGS.get(item.strip().lower())
                if alignment is None:
                    setter(Qt.AlignmentFlag(0))
                    return
                
                result |= alignment

        case _:
            pass
    
    setter(result)
    
    if store is not None:
        store[target].add('alignment')


QT_HANDLERS: tuple[QTHandler, ...] = (
    _apply_margin,
    _apply_spacing,
    _apply_alignment,
)


__all__ = (
    'QT_HANDLERS',
)
