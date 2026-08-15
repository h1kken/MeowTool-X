from __future__ import annotations

import typing as t

from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import QLayout, QWidget, QPushButton

from src.ui.icons.renderer import build_icon_pixmap

from .constants import ALIGNMENT_FLAGS
from .helpers import parse_box_values, to_int

if t.TYPE_CHECKING:
    from src.core.types import DataMap
    from .types import QTHandler


# margin
def _apply_margin(target: QObject, styles: DataMap, *, storage: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, QLayout):
        return
    
    margin = styles.get('margin')
    if isinstance(margin, str):
        margin = margin.split()

    if not isinstance(margin, list):
        return

    top, right, bottom, left = parse_box_values(styles, property_name='margin')
    target.setContentsMargins(left, top, right, bottom)
    
    if storage is not None:
        storage[target].add('margin')


# spacing
def _apply_spacing(target: QObject, styles: DataMap, *, storage: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, QLayout):
        return
    
    spacing = to_int(styles.get('spacing'))
    if spacing is None:
        target.setSpacing(0)
        return
    
    target.setSpacing(spacing)
    
    if storage is not None:
        storage[target].add('spacing')


# align
def _apply_alignment(target: QObject, styles: DataMap, *, storage: dict[QObject, set[str]] | None = None) -> None:
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
    
    if storage is not None:
        storage[target].add('alignment')


# icon
def _apply_icon(target: QObject, styles: DataMap, *, storage: dict[QObject, set[str]] | None = None) -> None:
    if not isinstance(target, (QPushButton)):
        return
    
    icon = styles.get('icon')
    if not isinstance(icon, dict):
        return

    source = icon.get('source')
    if source is None:
        target.setIcon(QIcon())
        return
    if not isinstance(source, str) or not source:
        return

    color = icon.get('color')
    if not isinstance(color, str) or not QColor(color).isValid():
        color = '#000000'

    rotation = icon.get('rotation')
    if not isinstance(rotation, (int, float)):
        rotation = 0

    w, h = _resolve_icon_size(icon.get('size'))

    pixmap = build_icon_pixmap(
        source=source,
        color=color,
        rotation=rotation,
        w=w,
        h=h,
    )

    target.setIcon(QIcon(pixmap) if not pixmap.isNull() else QIcon())
        
    if storage is not None:
        storage[target].add('icon')

def _resolve_icon_size(size: object) -> tuple[int, int]:
    if isinstance(size, dict):
        size = t.cast(dict[str, object], size)
        w = size.get('w', size.get('width', 16))
        h = size.get('h', size.get('height', 16))

    elif isinstance(size, str):
        values = size.split()
        match len(values):
            
            case 1:
                w = h = to_int(values[0])
                
            case 2:
                w, h = map(to_int, values)
                
            case _:
                return 16, 16  

    else:
        return 16, 16

    if not isinstance(w, int):
        w = 16

    if not isinstance(h, int):
        h = 16

    return w, h


QT_HANDLERS: tuple[QTHandler, ...] = (
    _apply_margin,
    _apply_spacing,
    _apply_alignment,
    _apply_icon,
)


__all__ = (
    'QT_HANDLERS',
)
