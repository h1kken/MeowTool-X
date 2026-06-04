from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from src.theme.animation.parser import normalize_specs_payload

BORDER_SIDE_KEYS = ('top', 'right', 'bottom', 'left')
BORDER_GLOBAL_KEYS = ('width', 'style', 'color', 'radius')


def normalize_theme_payload(theme: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(theme, dict):
        return {'widgets': {}}

    resolved_theme = resolve_theme_vars(theme)
    normalized = {
        key: deepcopy(value)
            for key, value in resolved_theme.items()
                if key not in {'widgets', 'vars'}
    }
    normalized['widgets'] = parse_widgets(resolved_theme.get('widgets', []))
    return normalized


def resolve_theme_vars(theme: dict[str, Any]) -> dict[str, Any]:
    raw_vars = theme.get('vars', {})
    vars_map = _normalize_theme_vars(raw_vars)
    if not vars_map:
        return deepcopy(theme)

    resolved_vars = _resolve_var_map(vars_map)
    resolved_theme = {
        key: _resolve_theme_value(value, resolved_vars)
            for key, value in theme.items()
                if key != 'vars'
    }
    resolved_theme['vars'] = resolved_vars
    return resolved_theme


def _normalize_theme_vars(raw_vars: Any) -> dict[str, Any]:
    if not isinstance(raw_vars, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key, value in raw_vars.items():
        if not isinstance(key, str):
            continue

        name = key.strip()
        if not name:
            continue
        if not name.startswith('--'):
            name = f'--{name}'

        normalized[name] = deepcopy(value)

    return normalized


def _resolve_var_map(vars_map: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}

    def resolve_var(name: str, stack: tuple[str, ...]) -> Any:
        if name in resolved:
            return deepcopy(resolved[name])
        if name in stack:
            return deepcopy(vars_map.get(name))
        if name not in vars_map:
            return None

        value = _resolve_theme_value(vars_map[name], vars_map, stack + (name,))
        resolved[name] = deepcopy(value)
        return deepcopy(value)

    for name in vars_map:
        resolve_var(name, ())

    return resolved


def _resolve_theme_value(value: Any, vars_map: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    if isinstance(value, str):
        ref = _normalize_var_reference(value)
        if ref is None or ref not in vars_map:
            return value
        if ref in stack:
            return value
        resolved = vars_map[ref]
        return _resolve_theme_value(deepcopy(resolved), vars_map, stack + (ref,))

    if isinstance(value, list):
        return [_resolve_theme_value(item, vars_map, stack) for item in value]

    if isinstance(value, dict):
        return {
            key: _resolve_theme_value(item, vars_map, stack)
            for key, item in value.items()
        }

    return deepcopy(value)


def parse_widgets(widgets: Any) -> dict[str, dict]:
    parsed: dict[str, dict[str, dict]] = {}
    if not isinstance(widgets, list):
        return parsed

    for item in widgets:
        if not isinstance(item, dict):
            continue

        targets = item.get('targets', [])
        if not isinstance(targets, list):
            continue

        raw_styles = item.get('styles', {})
        styles = normalize_widget_styles(raw_styles if isinstance(raw_styles, dict) else {})
        animations = item.get('animations')

        for obj_name in targets:
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


def merge_animation_data(current: Any, incoming: Any) -> Any:
    current_specs = normalize_specs_payload(current)
    incoming_specs = normalize_specs_payload(incoming)

    if not current_specs and not incoming_specs:
        return None

    merged: list[dict[str, Any]] = []
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


def merge_widget_theme_data(current: dict[str, Any] | None, incoming: dict[str, Any] | None) -> dict[str, Any]:
    base = current if isinstance(current, dict) else {}
    extra = incoming if isinstance(incoming, dict) else {}

    merged = deep_merge_dicts(
        {key: value for key, value in base.items() if key != 'animations'},
        {key: value for key, value in extra.items() if key != 'animations'},
    )

    animations = merge_animation_data(
        base.get('animations'),
        extra.get('animations'),
    )
    if animations:
        merged['animations'] = animations

    return merged


def deep_merge_dicts(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            if key == 'border' and _is_side_only_border(value):
                merged[key] = deepcopy(value)
            else:
                merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def normalize_widget_styles(styles: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(styles) if isinstance(styles, dict) else {}
    _fold_border_side_keys(normalized)

    background = normalized.get('background') if isinstance(normalized.get('background'), dict) else None
    if isinstance(background, dict) and 'radius' in background:
        border = normalized.get('border') if isinstance(normalized.get('border'), dict) else {}
        if not isinstance(border, dict):
            border = {}
        if 'radius' not in border:
            border['radius'] = deepcopy(background['radius'])
            normalized['border'] = border

    layout = normalized.get('layout') if isinstance(normalized.get('layout'), dict) else {}
    if layout:
        normalized['layout'] = layout

    return normalized


def _fold_border_side_keys(styles: dict[str, Any]) -> None:
    border = styles.get('border') if isinstance(styles.get('border'), dict) else {}
    changed = False

    for side in BORDER_SIDE_KEYS:
        for key in (f'border-{side}', f'border_{side}'):
            if key in styles:
                border[side] = _normalize_side_border_value(styles.pop(key))
                changed = True

        for field in ('width', 'style', 'color'):
            for key in (f'border-{side}-{field}', f'border_{side}_{field}'):
                if key not in styles:
                    continue
                side_data = border.get(side) if isinstance(border.get(side), dict) else {}
                side_data[field] = deepcopy(styles.pop(key))
                border[side] = side_data
                changed = True

    if changed:
        styles['border'] = border


def _normalize_side_border_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    if not isinstance(value, str):
        return {}

    width, style, color = _parse_border_shorthand(value)
    result: dict[str, Any] = {}
    if width:
        result['width'] = width
    if style:
        result['style'] = style
    if color:
        result['color'] = color
    return result


def _parse_border_shorthand(value: str) -> tuple[str | None, str | None, str | None]:
    text = str(value).strip().rstrip(';').strip()
    if not text:
        return None, None, None
    if ':' in text:
        text = text.split(':', 1)[1].strip()
    match = re.match(r'^(\S+)\s+(\S+)\s+(.+)$', text)
    if not match:
        return None, None, None
    return match.group(1), match.group(2), match.group(3).strip()


def _is_side_only_border(data: dict[str, Any]) -> bool:
    if any(key in data for key in BORDER_GLOBAL_KEYS):
        return False
    return any(key in data for key in BORDER_SIDE_KEYS)


def _normalize_var_reference(value: str) -> str | None:
    token = value.strip()
    if not token:
        return None

    if token.startswith('var(') and token.endswith(')'):
        token = token[4:-1].strip()

    if not token.startswith('--'):
        return None

    return token
