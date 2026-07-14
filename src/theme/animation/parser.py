from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, cast

from src.utils.conversion import as_dict

from .helpers import (
    normalize_token,
    parse_easing,
    parse_loop_count,
)
from .types import AnimationSpec
from src.theme.colors import to_qcolor

_NUMBER_VALUE_PATTERN = re.compile(r'^\s*([-+]?\d+(?:[.,]\d+)?)\s*(?:px)?\s*$', re.IGNORECASE)


def _iterable_items(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        items = cast(list[Any] | tuple[Any, ...] | set[Any], value)
        return list(items)
    return []


def parse_specs(raw: Any) -> list[AnimationSpec]:
    specs: list[AnimationSpec] = []
    for payload in normalize_specs_payload(raw):
        spec = _build_spec(payload)
        if spec is not None:
            specs.append(spec)
    return specs


def normalize_specs_payload(raw: Any) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []

    if isinstance(raw, list):
        items = cast(list[Any], raw)
        for item in items:
            _collect_payload_specs(payloads, item, default_action=None)
        return payloads

    if isinstance(raw, dict):
        mapping = cast(dict[str, Any], raw)
        if _looks_like_spec(mapping):
            _collect_payload_specs(payloads, mapping, default_action=None)
            return payloads

        for action, payload in mapping.items():
            _collect_payload_specs(payloads, payload, default_action=action)

    return payloads


def _collect_payload_specs(output: list[dict[str, Any]], payload: Any, default_action: str | None) -> None:
    if isinstance(payload, list):
        items = cast(list[Any], payload)
        for item in items:
            _collect_payload_specs(output, item, default_action)
        return

    if isinstance(payload, dict):
        mapping = cast(dict[str, Any], payload)
        if default_action and not any(key in mapping for key in ('on', 'action', 'state', 'event')):
            candidate: dict[str, Any] = {'on': default_action, **deepcopy(mapping)}
        else:
            candidate = deepcopy(mapping)

        spec_payloads = _normalize_raw_specs(candidate)
        if spec_payloads:
            output.extend(spec_payloads)
            return

        actions = _normalize_actions(_action_value(candidate, default_action))
        if not actions:
            return

        common: dict[str, Any] = {}
        if 'duration' in candidate or 'duration_ms' in candidate:
            common['duration'] = candidate.get('duration', candidate.get('duration_ms'))
        if 'easing' in candidate or 'curve' in candidate:
            common['easing'] = candidate.get('easing', candidate.get('curve'))
        if 'from' in candidate or 'start' in candidate:
            common['from'] = candidate.get('from', candidate.get('start'))
        if 'loop' in candidate or 'loops' in candidate or 'iterations' in candidate:
            common['loop'] = candidate.get('loop', candidate.get('loops', candidate.get('iterations')))

        skip_keys = {
            'on', 'action', 'state', 'event',
            'duration', 'duration_ms', 'easing', 'curve',
            'from', 'start', 'to', 'end', 'value',
            'loop', 'loops', 'iterations',
        }

        for action in actions:
            for prop, value in candidate.items():
                if prop in skip_keys:
                    continue

                for expanded in _expand_shorthand(action, prop, deepcopy(value), common):
                    output.extend(_normalize_raw_specs(expanded))
        return

    if default_action is not None and payload is not None:
        output.extend(_normalize_raw_specs({'on': default_action, 'property': 'background.color', 'to': deepcopy(payload)}))


def _action_value(raw: dict[str, Any], default_action: str | None = None) -> Any:
    for key in ('on', 'action', 'state', 'event'):
        if key in raw:
            return raw.get(key)
    return default_action


def _normalize_raw_specs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for action in _normalize_actions(_action_value(raw)):
        candidate = deepcopy(raw)
        candidate['on'] = action
        spec = _normalize_raw_spec(candidate)
        if spec is not None:
            specs.append(spec)
    return specs


def _normalize_raw_spec(raw: dict[str, Any]) -> dict[str, Any] | None:
    action = _normalize_action(_action_value(raw))
    if not action:
        return None

    prop = raw.get('property', raw.get('prop'))
    if not isinstance(prop, str):
        return None

    property_data = _normalize_property(prop)
    if property_data is None:
        return None

    property_key, _, _ = property_data
    end_raw = raw.get('to', raw.get('end', raw.get('value')))
    if end_raw is None:
        return None

    normalized: dict[str, Any] = {
        'on': action,
        'property': property_key,
        'to': deepcopy(end_raw),
    }

    start_raw = raw.get('from', raw.get('start'))
    if start_raw is not None:
        normalized['from'] = deepcopy(start_raw)

    if 'duration' in raw or 'duration_ms' in raw:
        normalized['duration'] = deepcopy(raw.get('duration', raw.get('duration_ms')))

    if 'easing' in raw or 'curve' in raw:
        normalized['easing'] = deepcopy(raw.get('easing', raw.get('curve')))

    if 'loop' in raw or 'loops' in raw or 'iterations' in raw:
        normalized['loop'] = deepcopy(raw.get('loop', raw.get('loops', raw.get('iterations'))))

    return normalized


def _expand_shorthand(action: str, prop: str, value: Any, common: dict[str, Any]) -> list[dict[str, Any]]:
    key = normalize_token(prop)
    specs: list[dict[str, Any]] = []

    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        match key:
            case 'background' | 'bg':
                if 'color' in mapping:
                    specs.append({'on': action, 'property': 'background.color', 'to': mapping['color'], **common})
            case 'text':
                if 'color' in mapping:
                    specs.append({'on': action, 'property': 'color', 'to': mapping['color'], **common})
            case 'border':
                if 'color' in mapping:
                    specs.append({'on': action, 'property': 'border.color', 'to': mapping['color'], **common})
                if 'width' in mapping:
                    specs.append({'on': action, 'property': 'border.width', 'to': mapping['width'], **common})
                if 'radius' in mapping:
                    specs.append({'on': action, 'property': 'border.radius', 'to': mapping['radius'], **common})
            case 'padding':
                for side in ('left', 'top', 'right', 'bottom'):
                    if side in mapping:
                        specs.append({'on': action, 'property': f'padding.{side}', 'to': mapping[side], **common})
            case 'layout':
                if 'spacing' in mapping:
                    specs.append({'on': action, 'property': 'layout.spacing', 'to': mapping['spacing'], **common})
                margin = as_dict(mapping.get('margin', mapping.get('margins'))) or {}
                if margin:
                    for side in ('left', 'top', 'right', 'bottom'):
                        if side in margin:
                            specs.append({'on': action, 'property': f'layout.margin.{side}', 'to': margin[side], **common})
                for side in ('left', 'top', 'right', 'bottom'):
                    for key_name in (f'margin_{side}', f'margin-{side}'):
                        if key_name in mapping:
                            specs.append({'on': action, 'property': f'layout.margin.{side}', 'to': mapping[key_name], **common})
            case 'parts':
                specs.extend(_expand_parts_shorthand(action, mapping, common))
            case _:
                pass
        return specs

    specs.append({'on': action, 'property': prop, 'to': value, **common})
    return specs


def _expand_parts_shorthand(action: str, value: dict[str, Any], common: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for part, part_data in value.items():
        part_name = normalize_token(part)
        if not isinstance(part_data, dict) or not part_name:
            continue
        mapping = cast(dict[str, Any], part_data)

        if 'color' in mapping:
            specs.append({'on': action, 'property': f'parts.{part_name}.color', 'to': mapping['color'], **common})
        for metric in ('width', 'height', 'size', 'rotation'):
            if metric in mapping:
                specs.append({'on': action, 'property': f'parts.{part_name}.{metric}', 'to': mapping[metric], **common})

        background = as_dict(mapping.get('background')) or {}
        if 'color' in background:
            specs.append({'on': action, 'property': f'parts.{part_name}.background.color', 'to': background['color'], **common})

        border = as_dict(mapping.get('border')) or {}
        if 'color' in border:
            specs.append({'on': action, 'property': f'parts.{part_name}.border.color', 'to': border['color'], **common})
        if 'width' in border:
            specs.append({'on': action, 'property': f'parts.{part_name}.border.width', 'to': border['width'], **common})
        if 'radius' in border:
            specs.append({'on': action, 'property': f'parts.{part_name}.border.radius', 'to': border['radius'], **common})

        text = as_dict(mapping.get('text')) or {}
        if 'color' in text:
            specs.append({'on': action, 'property': f'parts.{part_name}.text.color', 'to': text['color'], **common})

        states = as_dict(mapping.get('states')) or {}
        for state, state_data in states.items():
            state_name = normalize_token(state)
            if not isinstance(state_data, dict) or not state_name:
                continue
            state_mapping = cast(dict[str, Any], state_data)

            state_background = as_dict(state_mapping.get('background')) or {}
            if 'color' in state_background:
                specs.append({
                    'on': action,
                    'property': f'parts.{part_name}.states.{state_name}.background.color',
                    'to': state_background['color'],
                    **common,
                })

            state_text = as_dict(state_mapping.get('text')) or {}
            if 'color' in state_text:
                specs.append({
                    'on': action,
                    'property': f'parts.{part_name}.states.{state_name}.text.color',
                    'to': state_text['color'],
                    **common,
                })

            state_border = as_dict(state_mapping.get('border')) or {}
            if 'color' in state_border:
                specs.append({
                    'on': action,
                    'property': f'parts.{part_name}.states.{state_name}.border.color',
                    'to': state_border['color'],
                    **common,
                })
    return specs


def _build_spec(raw: dict[str, Any]) -> AnimationSpec | None:
    action = _normalize_action(_action_value(raw))
    if not action:
        return None

    prop = raw.get('property', raw.get('prop'))
    if not isinstance(prop, str):
        return None

    property_data = _normalize_property(prop)
    if property_data is None:
        return None

    property_key, kind, css_property = property_data
    loop_count = parse_loop_count(
        raw.get('loop', raw.get('loops', raw.get('iterations'))),
        default=-1 if action == 'always' else 1,
    )

    end_raw = raw.get('to', raw.get('end', raw.get('value')))
    if end_raw is None:
        return None

    start_raw = raw.get('from', raw.get('start'))

    if kind == 'color':
        end_color = to_qcolor(end_raw)
        if end_color is None:
            return None

        start_color = to_qcolor(start_raw) if start_raw is not None else None

        return AnimationSpec(
            action=action,
            property_key=property_key,
            css_property=css_property,
            kind=kind,
            duration=_resolve_duration(raw, default=220),
            loop_count=loop_count,
            easing=parse_easing(raw.get('easing', raw.get('curve'))),
            start=start_color,
            end=end_color,
        )

    if kind == 'number':
        end_number = _to_number(end_raw)
        if end_number is None:
            return None

        start_number = _to_number(start_raw) if start_raw is not None else None

        return AnimationSpec(
            action=action,
            property_key=property_key,
            css_property=css_property,
            kind=kind,
            duration=_resolve_duration(raw, default=220),
            loop_count=loop_count,
            easing=parse_easing(raw.get('easing', raw.get('curve'))),
            start=start_number,
            end=end_number,
            options={'duration_provided': 'duration' in raw or 'duration_ms' in raw},
        )

    return None


def _resolve_duration(raw: dict[str, Any], *, default: int) -> int:
    value = raw.get('duration', raw.get('duration_ms', default))
    try:
        duration = int(value)
    except (TypeError, ValueError):
        duration = default
    return max(duration, 1)


def _to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        match = _NUMBER_VALUE_PATTERN.fullmatch(text)
        if match:
            token = str(match.group(1)).replace(',', '.')
            try:
                return float(token)
            except ValueError:
                return None

        try:
            return float(text.replace(',', '.'))
        except ValueError:
            return None

    return None


def _looks_like_spec(data: Any) -> bool:
    if not isinstance(data, dict):
        return False

    if 'property' in data or 'prop' in data:
        return True

    if any(key in data for key in ('to', 'end', 'value')) and any(key in data for key in ('on', 'action', 'state', 'event')):
        return True

    return False


def _normalize_actions(action: Any) -> list[str]:
    if isinstance(action, str):
        values = [part.strip() for part in re.split(r'[,|]', action) if part.strip()]
    elif isinstance(action, (list, tuple, set)):
        values = _iterable_items(action)
    else:
        values = [action]

    actions: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_action(value)
        if normalized and normalized not in seen:
            actions.append(normalized)
            seen.add(normalized)
    return actions


def _normalize_action(action: Any) -> str:
    if not isinstance(action, str):
        return ''

    key = normalize_token(action)
    aliases = {
        'hover': 'hover',
        'enter': 'hover',
        'leave': 'leave',
        'out': 'leave',
        'press': 'press',
        'down': 'press',
        'mousedown': 'press',
        'release': 'release',
        'up': 'release',
        'mouseup': 'release',
        'focus': 'focus',
        'focusin': 'focus',
        'blur': 'blur',
        'focusout': 'blur',
        'click': 'click',
        'clicked': 'click',
        'doubleclick': 'double_click',
        'dblclick': 'double_click',
        'double_click': 'double_click',
        'open': 'open',
        'opened': 'open',
        'popupopen': 'open',
        'popup_open': 'open',
        'close': 'close',
        'closed': 'close',
        'popupclose': 'close',
        'popup_close': 'close',
        'wheel': 'wheel',
        'scroll': 'wheel',
        'mousewheel': 'wheel',
        'enabled': 'enabled',
        'enable': 'enabled',
        'disabled': 'disabled',
        'disable': 'disabled',
        'checked': 'checked',
        'check': 'checked',
        'on': 'checked',
        'toggle_on': 'checked',
        'unchecked': 'unchecked',
        'uncheck': 'unchecked',
        'off': 'unchecked',
        'toggle_off': 'unchecked',
        'always': 'always',
        'idle': 'always',
        'persistent': 'always',
    }
    return aliases.get(key, '')


def _normalize_property(prop: str) -> tuple[str, str, str] | None:
    key = normalize_token(prop)
    aliases = {
        'background': 'background.color',
        'bg': 'background.color',
        'background_color': 'background.color',
        'color': 'color',
        'text': 'color',
        'text_color': 'color',
        'border_color': 'border.color',
        'border_width': 'border.width',
        'border_radius': 'border.radius',
        'radius': 'border.radius',
        'padding_left': 'padding.left',
        'padding_top': 'padding.top',
        'padding_right': 'padding.right',
        'padding_bottom': 'padding.bottom',
        'margin_left': 'layout.margin.left',
        'margin_top': 'layout.margin.top',
        'margin_right': 'layout.margin.right',
        'margin_bottom': 'layout.margin.bottom',
        'layout_spacing': 'layout.spacing',
        'spacing': 'layout.spacing',
        'width': 'widget.maximum_width',
        'max_width': 'widget.maximum_width',
        'maximum_width': 'widget.maximum_width',
        'min_width': 'widget.minimum_width',
        'minimum_width': 'widget.minimum_width',
        'fixed_width': 'widget.width',
        'height': 'widget.maximum_height',
        'max_height': 'widget.maximum_height',
        'maximum_height': 'widget.maximum_height',
        'min_height': 'widget.minimum_height',
        'minimum_height': 'widget.minimum_height',
        'fixed_height': 'widget.height',
        'x': 'widget.x',
        'pos_x': 'widget.x',
        'position_x': 'widget.x',
        'y': 'widget.y',
        'pos_y': 'widget.y',
        'position_y': 'widget.y',
        'scroll_y': 'scroll.vertical',
        'scroll_vertical': 'scroll.vertical',
        'vertical_scroll': 'scroll.vertical',
        'viewport_scroll_y': 'scroll.vertical',
        'scroll_x': 'scroll.horizontal',
        'scroll_horizontal': 'scroll.horizontal',
        'horizontal_scroll': 'scroll.horizontal',
        'viewport_scroll_x': 'scroll.horizontal',
    }

    canonical = aliases.get(key)
    if canonical is None and '.' in prop:
        parts = [normalize_token(p) for p in prop.split('.') if p]
        canonical = '.'.join(parts)

    match canonical:
        case 'background.color':
            return canonical, 'color', 'background-color'
        case 'color':
            return canonical, 'color', 'color'
        case 'border.color':
            return canonical, 'color', 'border-color'
        case 'border.width':
            return canonical, 'number', ''
        case 'border.radius':
            return canonical, 'number', ''
        case 'padding.left' | 'padding.top' | 'padding.right' | 'padding.bottom':
            return canonical, 'number', ''
        case 'layout.spacing':
            return canonical, 'number', ''
        case 'layout.margin.left' | 'layout.margin.top' | 'layout.margin.right' | 'layout.margin.bottom':
            return canonical, 'number', ''
        case 'widget.width':
            return canonical, 'number', ''
        case 'widget.minimum_width':
            return canonical, 'number', ''
        case 'widget.maximum_width':
            return canonical, 'number', ''
        case 'widget.height':
            return canonical, 'number', ''
        case 'widget.minimum_height':
            return canonical, 'number', ''
        case 'widget.maximum_height':
            return canonical, 'number', ''
        case 'widget.x':
            return canonical, 'number', ''
        case 'widget.y':
            return canonical, 'number', ''
        case 'scroll.vertical':
            return canonical, 'number', ''
        case 'scroll.horizontal':
            return canonical, 'number', ''
        case _:
            pass

    if isinstance(canonical, str) and canonical.startswith('parts.'):
        parts = canonical.split('.')
        if len(parts) == 6 and parts[2] == 'states':
            if parts[4] == 'background' and parts[5] == 'color':
                return canonical, 'color', f'parts.{parts[1]}.states.{parts[3]}.background-color'
            if parts[4] == 'text' and parts[5] == 'color':
                return canonical, 'color', f'parts.{parts[1]}.states.{parts[3]}.color'
            if parts[4] == 'border' and parts[5] == 'color':
                return canonical, 'color', f'parts.{parts[1]}.states.{parts[3]}.border-color'
        if len(parts) == 3 and parts[2] == 'color':
            return canonical, 'color', f'parts.{parts[1]}.color'
        if len(parts) == 4 and parts[2] == 'background' and parts[3] == 'color':
            return canonical, 'color', f'parts.{parts[1]}.background-color'
        if len(parts) == 4 and parts[2] == 'text' and parts[3] == 'color':
            return canonical, 'color', f'parts.{parts[1]}.color'
        if len(parts) == 4 and parts[2] == 'border' and parts[3] == 'color':
            return canonical, 'color', f'parts.{parts[1]}.border-color'
        if len(parts) == 4 and parts[2] == 'border' and parts[3] in {'width', 'radius'}:
            return canonical, 'number', ''
        if len(parts) == 3 and parts[2] in {'width', 'height', 'size', 'rotation'}:
            return canonical, 'number', ''
        if len(parts) == 3 and parts[1] == 'groove' and parts[2] == 'size':
            return canonical, 'number', ''
        if len(parts) == 3 and parts[1] == 'handle' and parts[2] in {'width', 'height'}:
            return canonical, 'number', ''

    return None
