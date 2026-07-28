from __future__ import annotations

import re
from copy import deepcopy
import typing as t

type ThemeMap = dict[str, t.Any]

BORDER_SIDE_KEYS = ('top', 'right', 'bottom', 'left')
BORDER_GLOBAL_KEYS = ('width', 'style', 'color', 'radius')


def normalize_theme_payload(
    theme: dict[str, t.Any],
    *,
    include_animations: bool = True,
) -> dict[str, t.Any]:
    resolved_theme = resolve_theme_vars(theme)
    normalized = {
        key: deepcopy(value)
            for key, value in resolved_theme.items()
                if key not in {'widgets', 'vars'}
    }
    normalized['widgets'] = parse_widgets(
        resolved_theme.get('widgets', []),
        include_animations=include_animations,
    )
    return normalized


def resolve_theme_vars(theme: dict[str, t.Any]) -> dict[str, t.Any]:
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


def _normalize_theme_vars(raw_vars: t.Any) -> dict[str, t.Any]:
    if not isinstance(raw_vars, dict):
        return {}

    normalized: ThemeMap = {}
    for key, value in t.cast(ThemeMap, raw_vars).items():
        name = key.strip()
        if not name:
            continue
        if not name.startswith('--'):
            name = f'--{name}'

        normalized[name] = deepcopy(value)

    return normalized


def _resolve_var_map(vars_map: dict[str, t.Any]) -> dict[str, t.Any]:
    resolved: dict[str, t.Any] = {}

    def resolve_var(name: str, stack: tuple[str, ...]) -> t.Any:
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


def _resolve_theme_value(value: t.Any, vars_map: dict[str, t.Any], stack: tuple[str, ...] = ()) -> t.Any:
    if isinstance(value, str):
        ref = _normalize_var_reference(value)
        if ref is None or ref not in vars_map:
            return value
        if ref in stack:
            return value
        resolved = vars_map[ref]
        return _resolve_theme_value(deepcopy(resolved), vars_map, stack + (ref,))

    if isinstance(value, list):
        return [_resolve_theme_value(item, vars_map, stack) for item in t.cast(list[t.Any], value)]

    if isinstance(value, dict):
        return {
            key: _resolve_theme_value(item, vars_map, stack)
            for key, item in t.cast(ThemeMap, value).items()
        }

    return deepcopy(value)


def parse_widgets(
    widgets: t.Any,
    *,
    include_animations: bool = True,
) -> dict[str, ThemeMap]:
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
    from src.theme.animation.parser import normalize_specs_payload

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


def _fold_border_side_keys(styles: dict[str, t.Any]) -> None:
    raw_border = styles.get('border')
    border = t.cast(ThemeMap, raw_border) if isinstance(raw_border, dict) else {}
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
                raw_side_data = border.get(side)
                side_data = t.cast(ThemeMap, raw_side_data) if isinstance(raw_side_data, dict) else {}
                side_data[field] = deepcopy(styles.pop(key))
                border[side] = side_data
                changed = True

    if changed:
        styles['border'] = border


def _normalize_side_border_value(value: t.Any) -> dict[str, t.Any]:
    if isinstance(value, dict):
        return deepcopy(t.cast(ThemeMap, value))
    if not isinstance(value, str):
        return {}

    width, style, color = _parse_border_shorthand(value)
    result: dict[str, t.Any] = {}
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


def _is_side_only_border(data: dict[str, t.Any]) -> bool:
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
