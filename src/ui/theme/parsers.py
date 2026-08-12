from __future__ import annotations

import typing as t

from .constants import SIDES
from .helpers import parse_sides

if t.TYPE_CHECKING:
    from src.core.types import DataValue, DataMap
    from .types import QSSParser


def _parse_gradient_color(styles: DataMap) -> str:
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


def _parse_linear_gradient(styles: DataMap) -> str:
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


def _parse_radial_gradient(styles: DataMap) -> str:
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


def _parse_conical_gradient(styles: DataMap) -> str:
    center = _parse_gradient_point(styles.get('center'))
    stops = _parse_gradient_stops(styles.get('stops'))
    if center is None or not stops:
        return ''

    angle = styles.get('angle')
    if not isinstance(angle, (int, float)):
        return ''

    angle = float(angle)
    cx, cy = center

    return f'qconicalgradient(cx:{cx}, cy:{cy}, angle:{angle}, {stops})'


def _parse_gradient_point(value: DataValue) -> tuple[float, float] | None:
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


def _parse_gradient_stops(stops: DataValue) -> str:
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


# text
def _parse_text(styles: DataMap) -> list[str]:
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


def _parse_text_font(styles: DataMap) -> list[str]:
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
def _parse_background(styles: DataMap) -> list[str]:
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


def _parse_background_color(styles: DataValue) -> list[str]:
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
def _parse_border(styles: DataMap) -> list[str]:
    border = styles.get('border')
    rules: list[str] = []

    match border:
        
        case str():
            rule = _parse_border_str(border)
            if rule:
                rules.append(rule)
            
        case dict():
            if any(side in border for side in SIDES):
                rules.extend(_parse_border_sides(border))
            elif all(option in border and str(border[option]).strip() for option in ('width', 'style', 'color')):
                rules.append(f'border: {border['width']} {border['style']} {border['color']};')

            radius = str(border.get('radius', '')).strip()
            if radius and rules:
                rules.append(f'border-radius: {border['radius']};')

        case _:
            pass
    
    return rules


def _parse_border_sides(styles: DataMap) -> list[str]:
    rules: list[str] = []
    
    for side in SIDES:
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


# padding
def _parse_padding(styles: DataMap) -> list[str]:
    padding = styles.get('padding')
    rules: list[str] = []
    
    match padding:
        
        case str() | list():
            if isinstance(padding, str):
                padding = padding.split()
                
            if 1 <= len(padding) <= 4:
                rules.append(f'padding: {' '.join(map(str, padding))};')
        
        case dict():
            rules.extend(parse_sides(padding, property_name='padding'))
            
        case _:
            pass

    return rules


# qss
def _parse_qss(styles: DataMap) -> list[str]:
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


QSS_PARSERS: tuple[QSSParser, ...] = (
    _parse_text,
    _parse_background,
    _parse_border,
    _parse_padding,
    _parse_qss,
)


__all__ = (
    'QSS_PARSERS',
)
