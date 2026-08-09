from __future__ import annotations

import typing as t

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLayout, QWidget

if t.TYPE_CHECKING:
    from .types import ThemeMap, ThemeValue, QSSHandler, QTHandler


_SIDES = ('top', 'right', 'bottom', 'left')
_ALIGNMENT_FLAGS: dict[str, Qt.AlignmentFlag] = {
    'top': Qt.AlignmentFlag.AlignTop,
    'bottom': Qt.AlignmentFlag.AlignBottom,
    'left': Qt.AlignmentFlag.AlignLeft,
    'right': Qt.AlignmentFlag.AlignRight,
    'center': Qt.AlignmentFlag.AlignCenter,
    'hcenter': Qt.AlignmentFlag.AlignHCenter,
    'vcenter': Qt.AlignmentFlag.AlignVCenter,
    'justify': Qt.AlignmentFlag.AlignJustify,
    'baseline': Qt.AlignmentFlag.AlignBaseline,
    'absolute': Qt.AlignmentFlag.AlignAbsolute,
}


# vars
def _resolve_var_map(vars_map: ThemeMap) -> ThemeMap:
    resolved: ThemeMap = {}

    def resolve_var(name: str, stack: tuple[str, ...]) -> ThemeValue:
        if name in resolved:
            return resolved[name]

        if name in stack:
            return deepcopy(vars_map[name])

        value = _resolve_value(vars_map[name], stack + (name,))
        resolved[name] = value
        return value

    def _resolve_value(value: ThemeValue, stack: tuple[str, ...]) -> ThemeValue:
        if isinstance(value, str):
            ref = _normalize_var(value)

            if ref is None or ref not in vars_map:
                return value

            return resolve_var(ref, stack)

        if isinstance(value, list):
            return [_resolve_value(item, stack) for item in value]

        if isinstance(value, dict):
            return {
                key: _resolve_value(item, stack)
                for key, item in value.items()
            }

        return value

    for name in vars_map:
        resolve_var(name, ())

    return resolved


def _normalize_var(value: str) -> str | None:
    value = value.strip()

    if value.startswith("var("):
        if not value.endswith(")"):
            return None

        value = value[4:-1].strip()

    if not value.startswith("--"):
        return None

    if any(char.isspace() for char in value):
        return None

    return value


def _resolve_theme_value(value: ThemeValue, vars_map: ThemeMap) -> ThemeValue:
    if isinstance(value, str):
        ref = _normalize_var(value)
        if ref is None or ref not in vars_map:
            return value

        return deepcopy(vars_map[ref])

    if isinstance(value, list):
        return [_resolve_theme_value(item, vars_map) for item in value]

    if isinstance(value, dict):
        return {key: _resolve_theme_value(item, vars_map) for key, item in value.items()}

    return value


def parse_widgets(widgets: t.Any, *, include_animations: bool = True) -> dict[str, ThemeMap]:
    parsed: dict[str, ThemeMap] = {}
    if not isinstance(widgets, list):
        return parsed

    for item in t.cast(list[t.Any], widgets):
        if not isinstance(item, dict):
            continue
        item_map = t.cast(ThemeMap, item)

        targets = item_map.get('targets', [])
        if not isinstance(targets, list):
            continue

        raw_styles = item_map.get('styles', {})
        styles = normalize_widget_styles(t.cast(ThemeMap, raw_styles) if isinstance(raw_styles, dict) else {})
        style_animations = styles.pop('animations', None)
        animations = (
            merge_animation_data(style_animations, item_map.get('animations'))
            if include_animations
            else None
        )

        for obj_name in t.cast(list[t.Any], targets):
            if not isinstance(obj_name, str) or not obj_name:
                continue

            parsed.setdefault(obj_name, {})
            if styles:
                current_animations = parsed[obj_name].get('animations')
                merged_styles = deep_merge_dicts(
                    {key: value for key, value in parsed[obj_name].items() if key != 'animations'},
                    styles,
                )
                parsed[obj_name] = merged_styles
                if current_animations is not None:
                    parsed[obj_name]['animations'] = current_animations

            if animations is not None:
                merged_animations = merge_animation_data(
                    parsed[obj_name].get('animations'),
                    animations,
                )
                if merged_animations:
                    parsed[obj_name]['animations'] = merged_animations

    return parsed


def merge_animation_data(current: t.Any, incoming: t.Any) -> t.Any:
    from src.ui.theme.animation.parser import normalize_specs_payload

    current_specs = normalize_specs_payload(current)
    incoming_specs = normalize_specs_payload(incoming)

    if not current_specs and not incoming_specs:
        return None

    merged: list[dict[str, t.Any]] = []
    positions: dict[tuple[str, str], int] = {}

    for spec in current_specs:
        key = (str(spec.get('on', '')), str(spec.get('property', '')))
        positions[key] = len(merged)
        merged.append(deepcopy(spec))

    for spec in incoming_specs:
        key = (str(spec.get('on', '')), str(spec.get('property', '')))
        if key in positions:
            merged[positions[key]] = deepcopy(spec)
        else:
            positions[key] = len(merged)
            merged.append(deepcopy(spec))

    return merged


def deep_merge_dicts(current: dict[str, t.Any], incoming: dict[str, t.Any]) -> dict[str, t.Any]:
    merged = deepcopy(current)
    for key, value in incoming.items():
        existing = merged.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            value_map = t.cast(ThemeMap, value)
            existing_map = t.cast(ThemeMap, existing)
            if key == 'border' and _is_side_only_border(value_map):
                merged[key] = deepcopy(value_map)
            else:
                merged[key] = deep_merge_dicts(existing_map, value_map)
        else:
            merged[key] = deepcopy(t.cast(t.Any, value))
    return merged


def normalize_widget_styles(styles: dict[str, t.Any]) -> dict[str, t.Any]:
    normalized = deepcopy(styles)
    _fold_border_side_keys(normalized)

    raw_background = normalized.get('background')
    background = t.cast(ThemeMap, raw_background) if isinstance(raw_background, dict) else None
    if isinstance(background, dict) and 'radius' in background:
        raw_border = normalized.get('border')
        border = t.cast(ThemeMap, raw_border) if isinstance(raw_border, dict) else {}
        if 'radius' not in border:
            border['radius'] = deepcopy(background['radius'])
            normalized['border'] = border

    raw_layout = normalized.get('layout')
    layout = t.cast(ThemeMap, raw_layout) if isinstance(raw_layout, dict) else {}
    if layout:
        normalized['layout'] = layout

    return normalized


def _parse_gradient_color(styles: ThemeMap) -> str:
    gradient_type = str(styles.get('type', '')).strip().lower()

    match gradient_type:

        case 'linear':
            return _parse_linear_gradient(styles)

        case 'radial':
            return _parse_radial_gradient(styles)

        case 'conical':
            return _parse_conical_gradient(styles)

        case _:
            return ''


def _parse_linear_gradient(styles: ThemeMap) -> str:
    start = _parse_gradient_point(styles.get('start'))
    end = _parse_gradient_point(styles.get('end'))
    stops = _parse_gradient_stops(styles.get('stops'))

    if (
        start is None
        or end is None
        or not stops
    ):
        return ''

    x1, y1 = start
    x2, y2 = end

    return f'qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stops})'


def _parse_radial_gradient(styles: ThemeMap) -> str:
    center = _parse_gradient_point(styles.get('center'))
    stops = _parse_gradient_stops(styles.get('stops'))

    if center is None or not stops:
        return ''

    radius = styles.get('radius')
    
    if not isinstance(radius, (int, float)):
        return ''
    
    radius = float(radius)

    if radius <= 0:
        return ''

    cx, cy = center

    return f'qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {stops})'


def _parse_conical_gradient(styles: ThemeMap) -> str:
    center = _parse_gradient_point(styles.get('center'))
    angle = styles.get('angle')
    stops = _parse_gradient_stops(styles.get('stops'))

    if center is None or not stops:
        return ''

    angle = styles.get('angle')

    if not isinstance(angle, (int, float)):
        return ''

    angle = float(angle)
    cx, cy = center

    return f'qconicalgradient(cx:{cx}, cy:{cy}, angle:{angle}, {stops})'


def _parse_gradient_point(value: ThemeValue) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None

    x, y = value

    if not isinstance(x, (int, float)):
        return None
    
    if not isinstance(y, (int, float)):
        return None
    
    x = float(x)
    y = float(y)

    if not 0 <= x <= 1 or not 0 <= y <= 1:
        return None

    return x, y


def _parse_gradient_stops(stops: ThemeValue) -> str:
    if not isinstance(stops, list):
        return ''

    result: list[str] = []

    for stop in stops:
        if not isinstance(stop, (list, tuple)) or len(stop) != 2:
            continue

        position = stop[0]

        if not isinstance(position, (int, float)):
            return ''

        position = float(position)
        color = str(stop[1]).strip()

        if not 0 <= position <= 1 or not color:
            continue

        result.append(f'stop: {position} {color}')

    return ', '.join(result)


def _parse_sides(styles: ThemeMap, *, property_name: str) -> list[str]:
    rules: list[str] = []
    
    for side in _SIDES:
        value = styles.get(side)
        
        if value is None:
            continue
        
        rules.append(f'{property_name}-{side}: {value};')
    
    return rules


def _parse_box_values(styles: ThemeMap, *, name: str) -> tuple[int, int, int, int]:
    values: list[int] = [0, 0, 0, 0] # top right bottom left

    raw = styles.get(name)
    
    if isinstance(raw, str):
        raw = raw.split()

    match raw:
        
        case int() | float():
            values = [int(raw)] * 4

        case list():
            match len(raw):
                
                case 1:
                    number = _to_int(raw[0])
                    if number is not None:
                        values = [number] * 4

                case 2:
                    numbers = list(map(_to_int, (raw[0], raw[1])))
                    if _all_ints(numbers):
                        values = numbers * 2

                case 3:
                    numbers = list(map(_to_int, (raw[0], raw[1], raw[2], raw[1])))
                    if _all_ints(numbers):
                        values = numbers

                case 4:
                    numbers = list(map(_to_int, raw))
                    if _all_ints(numbers):
                        values = numbers

                case _:
                    pass

        case dict():
            for index, side in enumerate(_SIDES):
                if side in raw:
                    number = _to_int(raw[side])
                    if number is not None:
                        values[index] = number

        case _:
            pass

    for index, side in enumerate(_SIDES):
        key = f'{name}-{side}'

        if key in styles:
            number = _to_int(styles[key])
            if number is not None:
                values[index] = number

    return values[0], values[1], values[2], values[3]


def _to_int(value: object) -> int | None:
    match value:
        case int():
            return value

        case float():
            return int(value)

        case str():
            try:
                return int(value.strip())
            except ValueError:
                return None

        case _:
            return None


def _all_ints(values: list[int | None]) -> t.TypeGuard[list[int]]:
    return all(value is not None for value in values)


# text
def _parse_text(styles: ThemeMap) -> list[str]:
    text = styles.get('text')
    rules: list[str] = []

    match text:
        
        case dict():
            color = str(text.get('color', '')).strip()
            if color:
                rules.append(f'color: {color};')
            
            size = str(text.get('size', '')).strip()
            if size:
                rules.append(f'font-size: {size};')
            
            rules.extend(_parse_text_font(text))
            
        case _:
            pass

    return rules


def _parse_text_font(styles: ThemeMap) -> list[str]:
    font = styles.get('font')
    rules: list[str] = []
    
    match font:
        
        case dict():
            for option in ('family', 'style', 'weight'):
                value = str(font.get(option, '')).strip()
                if value:
                    rules.append(f'font-{option}: {value};')
            
        case _:
            pass
    
    return rules


# background
def _parse_background(styles: ThemeMap) -> list[str]:
    background = styles.get('background')
    rules: list[str] = []

    match background:
        
        case dict():
            color = background.get('color')
            if color:
                rules.extend(_parse_background_color(color))
    
        case _:
            pass

    return rules


def _parse_background_color(styles: ThemeValue) -> list[str]:
    rules: list[str] = []
    
    match styles:
        
        case str():
            color = styles.strip()
            if color:
                rules.append(color)
        
        case dict():
            rules.extend(_parse_gradient_color(styles))
        
        case _:
            pass
    
    return rules


# border | TODO: wrong
def _parse_border(styles: ThemeMap) -> list[str]:
    border = styles.get('border')
    rules: list[str] = []

    match border:
        
        case str():
            rule = _parse_border_str(border)
            if rule:
                rules.append(rule)
            
        case dict():
            if any(side in border for side in _SIDES):
                rules.extend(_parse_border_sides(border))
            elif all(option in border and str(border[option]).strip() for option in ('width', 'style', 'color')):
                rules.append(f'border: {border['width']} {border['style']} {border['color']};')

            radius = str(border.get('radius', '')).strip()
            if radius and rules:
                rules.append(f'border-radius: {border['radius']};')

        case _:
            pass
    
    return rules


def _parse_border_sides(styles: ThemeMap) -> list[str]:
    rules: list[str] = []
    
    for side in _SIDES:
        value = styles.get(side)

        match value:
            
            case str():
                rule = _parse_border_str(value, property_name=f'border-{side}')
                if rule:
                    rules.append(rule)
                
            case dict():
                if all(option in value and str(value.get(option, '')).strip() for option in ('width', 'style', 'color')):
                    rules.append(f'border-{side}: {value['width']} {value['style']} {value['color']};')
                
            case _:
                pass
    
    return rules

def _parse_border_str(styles: str, *, property_name: str = 'border') -> str:
    parts = styles.split()
    if len(parts) != 3:
        return ''

    width, style, color = parts
    return f'{property_name}: {width} {style} {color};'


# margin
def _apply_margin(layout: QLayout, styles: ThemeMap) -> None:
    margin = styles.get('margin')
    
    if isinstance(margin, str):
        margin = margin.split()

    if not isinstance(margin, list):
        return

    top, right, bottom, left = _parse_box_values(styles, name='margin')
    layout.setContentsMargins(left, top, right, bottom)


# padding
def _parse_padding(styles: ThemeMap) -> list[str]:
    padding = styles.get('padding')
    rules: list[str] = []
    
    match padding:
        
        case str() | list():
            if isinstance(padding, str):
                padding = padding.split()
                
            if 1 <= len(padding) <= 4:
                rules.append(f'padding: {' '.join(map(str, padding))};')
        
        case dict():
            rules.extend(_parse_sides(padding, property_name='padding'))
            
        case _:
            pass

    return rules


# spacing
def _apply_spacing(layout: QLayout, styles: ThemeMap) -> None:
    spacing = _to_int(styles.get('spacing'))
    if spacing is not None:
        layout.setSpacing(spacing)


# alignment
def _apply_alignment(target: QLayout | QWidget, styles: ThemeMap) -> None:
    setter = getattr(target, 'setAlignment', None)
    if not callable(setter):
        return
    
    result = Qt.AlignmentFlag(0)
    
    value = styles.get('align') or styles.get('alignment')
    
    match value:
        
        case str():
            alignment = _ALIGNMENT_FLAGS.get(value.strip().lower())
            if alignment is not None:
                result |= alignment

        case list():
            for item in value:
                if not isinstance(item, str):
                    setter(Qt.AlignmentFlag(0))
                    return
                    
                alignment = _ALIGNMENT_FLAGS.get(item.strip().lower())
                if alignment is None:
                    setter(Qt.AlignmentFlag(0))
                    return
                
                result |= alignment

        case _:
            pass
    
    setter(result)


def _parse_qss(styles: ThemeMap) -> list[str]:
    raw = styles.get('qss')
    rules: list[str] = []
    
    match raw:
        
        case str():
            value = raw.strip()
            if value:
                rules.append(f'{value.rstrip(';')};')

        case dict():
            for raw_key, raw_value in raw.items():
                key = str(raw_key).strip()
                value = str(raw_value).strip()
                if key and value:
                    rules.append(f'{key}: {value};')

        case _:
            pass

    return rules


QSS_HANDLERS: tuple[QSSHandler, ...] = (
    _parse_text,
    _parse_background,
    _parse_border,
    _parse_padding,
    _parse_qss,
)


QT_HANDLERS: tuple[QTHandler, ...] = (
    _apply_margin,
    _apply_spacing,
    _apply_alignment,
)


__all__ = (
    'QSS_HANDLERS',
    'QT_HANDLERS',
)
