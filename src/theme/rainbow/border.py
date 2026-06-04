from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from src.theme.colors import normalize_color_or_raw, to_qcolor

CSS_BLOCK_PATTERN = re.compile(r'([^{}]+)\{([^{}]*)\}', re.DOTALL)
CSS_DECLARATION_PATTERN = re.compile(r'([a-zA-Z-]+)\s*:\s*([^;{}]+)')
BORDER_RADIUS_KEYS: tuple[str, ...] = (
    'border-radius',
    'border-top-left-radius',
    'border-top-right-radius',
    'border-bottom-right-radius',
    'border-bottom-left-radius',
)
BORDER_SIDE_KEYS: tuple[str, ...] = ('top', 'right', 'bottom', 'left')


def detect_border_config(
    widget: QWidget,
    *,
    fallback_width: float,
    fallback_radius: float,
) -> dict[str, Any]:
    declarations = collect_widget_declarations(widget)
    border_rule_text = widget.property('_themeBorderRule') if isinstance(widget.property('_themeBorderRule'), str) else None
    if not border_rule_text and isinstance(declarations.get('border'), str):
        border_rule_text = declarations.get('border')
    width_text = declarations.get('border-width')
    style_text = declarations.get('border-style')
    if border_rule_text:
        short_width, short_style, short_color = parse_border_shorthand(border_rule_text)
        width_text = width_text or short_width
        style_text = style_text or short_style
    else:
        short_color = None

    width = parse_measure_value(width_text)
    style = str(style_text or '').strip().lower()
    color_text = declarations.get('border-color') or short_color
    radius = parse_measure_value(declarations.get('border-radius'))
    if radius is None:
        radius = parse_measure_value(widget.property('_themeBorderRadius'))

    side_widths: dict[str, str] = {}
    side_styles: dict[str, str] = {}
    side_colors: dict[str, str] = {}
    for side in BORDER_SIDE_KEYS:
        side_width = declarations.get(f'border-{side}-width')
        side_style = declarations.get(f'border-{side}-style')
        side_color = declarations.get(f'border-{side}-color')
        if (side_shorthand := declarations.get(f'border-{side}')):
            short_side_width, short_side_style, short_side_color = parse_border_shorthand(side_shorthand)
            side_width = side_width or short_side_width
            side_style = side_style or short_side_style
            side_color = side_color or short_side_color
        if isinstance(side_width, str) and side_width.strip():
            side_widths[side] = side_width.strip()
        if isinstance(side_style, str) and side_style.strip():
            side_styles[side] = side_style.strip()
        if isinstance(side_color, str) and side_color.strip():
            side_colors[side] = side_color.strip()

    has_global_border = bool(width and width > 0.0 and style and style != 'none')
    has_side_border = any(
        (side_width := parse_measure_value(side_widths.get(side))) is not None
        and side_width > 0.0
        and (side_style := side_styles.get(side, style)).strip().lower()
        and side_style.strip().lower() != 'none'
        for side in BORDER_SIDE_KEYS
    )
    visible = has_global_border or has_side_border
    if visible:
        return {
            'native': True,
            'width': max(1.0, float(width or max((parse_measure_value(value) or 0.0 for value in side_widths.values()), default=1.0))),
            'style': style,
            'radius': max(0.0, float(radius)) if radius is not None else 0.0,
            'inset': 0.0,
            'border_rule_text': border_rule_text or '',
            'border_width_text': str(width_text).strip() if isinstance(width_text, str) else (f'{float(width):g}px' if width is not None else ''),
            'border_style_text': str(style_text).strip() if isinstance(style_text, str) else style,
            'border_color_text': str(color_text).strip() if isinstance(color_text, str) and color_text.strip() else '',
            'border_radius_rules': {
                key: str(value).strip()
                for key, value in declarations.items()
                if key in BORDER_RADIUS_KEYS and isinstance(value, str) and value.strip()
            },
            'border_side_widths': side_widths,
            'border_side_styles': side_styles,
            'border_side_colors': side_colors,
        }

    return {
        'native': False,
        'width': float(fallback_width),
        'style': 'solid',
        'radius': max(0.0, float(radius)) if radius is not None else float(fallback_radius),
        'inset': 0.0,
        'dash_pattern': [9999.0, 1.0],
        'pen_style': Qt.PenStyle.SolidLine,
    }


def build_native_border_transition_rules(
    config: dict[str, Any],
    rainbow_color: QColor,
    opacity: float,
) -> list[str]:
    mixed_global = mix_border_color(
        str(config.get('border_color_text', '') or ''),
        rainbow_color,
        opacity,
    )
    side_colors_raw = config.get('border_side_colors', {})
    side_colors_mixed = {
        side: mix_border_color(str(value or ''), rainbow_color, opacity)
        for side, value in side_colors_raw.items()
        if isinstance(value, str) and value.strip()
    }
    return build_native_border_color_rules(
        config,
        _format_qss_color(mixed_global),
        side_color_names={
            side: _format_qss_color(value)
            for side, value in side_colors_mixed.items()
        },
    )


def build_native_border_color_rules(
    config: dict[str, Any],
    color_name: str,
    *,
    side_color_names: dict[str, str] | None = None,
) -> list[str]:
    border_rule_text = str(config.get('border_rule_text', '') or '').strip()
    border_width_text = str(config.get('border_width_text', '') or '').strip()
    border_style_text = str(config.get('border_style_text', '') or '').strip()
    border_radius_rules = config.get('border_radius_rules', {})
    border_side_widths = config.get('border_side_widths', {})
    border_side_styles = config.get('border_side_styles', {})
    border_side_colors = config.get('border_side_colors', {})
    runtime_side_colors = {
        side: str(value).strip()
        for side, value in (side_color_names or {}).items()
        if isinstance(value, str) and value.strip()
    }

    rules: list[str] = []
    if border_rule_text:
        parsed_width, parsed_style, _ = parse_border_shorthand(border_rule_text)
        if parsed_width and parsed_style:
            rules.append(f'border: {parsed_width} {parsed_style} {color_name};')

    if not rules:
        if border_width_text:
            rules.append(f'border-width: {border_width_text};')
        if border_style_text:
            rules.append(f'border-style: {border_style_text};')

    for side, value in border_side_widths.items():
        rules.append(f'border-{side}-width: {value};')
    for side, value in border_side_styles.items():
        rules.append(f'border-{side}-style: {value};')

    if runtime_side_colors:
        for side in BORDER_SIDE_KEYS:
            side_color = runtime_side_colors.get(side)
            if isinstance(side_color, str) and side_color.strip():
                rules.append(f'border-{side}-color: {side_color};')
    elif isinstance(border_side_colors, dict) and border_side_colors:
        for side in BORDER_SIDE_KEYS:
            side_color = border_side_colors.get(side)
            if isinstance(side_color, str) and side_color.strip():
                rules.append(f'border-{side}-color: {color_name};')
    else:
        rules.extend([
            f'border-color: {color_name};',
            f'border-top-color: {color_name};',
            f'border-right-color: {color_name};',
            f'border-bottom-color: {color_name};',
            f'border-left-color: {color_name};',
        ])

    if isinstance(border_radius_rules, dict):
        for key, value in border_radius_rules.items():
            if isinstance(value, str) and value.strip():
                rules.append(f'{key}: {value.strip()};')

    rules.append('outline: 0;')
    return rules


def mix_border_color(base_color: Any, rainbow_color: QColor, opacity: float) -> QColor:
    mix = max(0.0, min(float(opacity), 1.0))
    target = QColor(rainbow_color)
    target.setAlpha(255)

    base = to_qcolor(base_color)
    if base is None:
        result = QColor(target)
        result.setAlpha(round(255 * mix))
        return result

    if mix <= 0.0:
        return base
    if mix >= 1.0:
        return target

    return QColor(
        round(base.red() + (target.red() - base.red()) * mix),
        round(base.green() + (target.green() - base.green()) * mix),
        round(base.blue() + (target.blue() - base.blue()) * mix),
        round(base.alpha() + (target.alpha() - base.alpha()) * mix),
    )


def combine_with_scoped_rules(widget: QWidget, base_style: str, rules: list[str]) -> str:
    rules_text = ''.join(rules)
    object_name = widget.objectName()
    if not object_name:
        return f'{base_style}\n{rules_text}'

    escaped_name = object_name.replace('\\', '\\\\').replace('"', '\\"')
    return f'{base_style}\n#{escaped_name} {{ {rules_text} }}'


def collect_widget_declarations(widget: QWidget) -> dict[str, str]:
    declarations: dict[str, str] = {}

    local_stylesheet = widget.styleSheet()
    if isinstance(local_stylesheet, str) and local_stylesheet.strip():
        declarations.update(extract_css_declarations(local_stylesheet))

    declarations.update(collect_stylesheet_declarations(widget))

    theme_border_rule = widget.property('_themeBorderRule')
    if isinstance(theme_border_rule, str) and theme_border_rule.strip():
        declarations.update(extract_css_declarations(theme_border_rule))

    theme_radius = widget.property('_themeBorderRadius')
    if isinstance(theme_radius, str) and theme_radius.strip():
        declarations['border-radius'] = theme_radius.strip()
    return declarations


def collect_stylesheet_declarations(widget: QWidget) -> dict[str, str]:
    declarations: dict[str, str] = {}
    root = widget.window()
    stylesheet = root.styleSheet() if isinstance(root, QWidget) else ''
    if not isinstance(stylesheet, str) or not stylesheet.strip():
        return declarations

    class_names = {cls.__name__ for cls in type(widget).mro() if isinstance(cls.__name__, str)}
    object_name = widget.objectName()
    for match in CSS_BLOCK_PATTERN.finditer(stylesheet):
        selector_text = str(match.group(1)).strip()
        body = str(match.group(2)).strip()
        if not selector_text or not body:
            continue

        selectors = [selector.strip() for selector in selector_text.split(',') if selector.strip()]
        if any(selector_matches_widget(selector, widget, object_name, class_names) for selector in selectors):
            declarations.update(extract_css_declarations(body))

    return declarations


def selector_matches_widget(
    selector: str,
    widget: QWidget,
    object_name: str,
    class_names: set[str],
) -> bool:
    text = selector.strip()
    if not text or ' ' in text or '>' in text or '+' in text or '~' in text:
        return False
    if ':' in text:
        return False

    base, properties = split_selector_properties(text)
    if not base:
        return False

    if base == '*':
        base_matches = True
    elif base.startswith('#'):
        base_matches = object_name and base[1:] == object_name
    else:
        base_matches = base in class_names
    if not base_matches:
        return False

    for key, expected in properties:
        if str(widget.property(key)) != expected:
            return False
    return True


def split_selector_properties(selector: str) -> tuple[str, list[tuple[str, str]]]:
    if '[' not in selector:
        return selector.strip(), []

    base = selector.split('[', 1)[0].strip()
    properties: list[tuple[str, str]] = []
    for match in re.finditer(r'\[([a-zA-Z_]\w*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\]]*))\]', selector):
        key = str(match.group(1)).strip()
        value = next(
            str(group).strip()
            for group in match.groups()[1:]
            if group is not None
        )
        if key:
            properties.append((key, value))
    return base, properties


def extract_css_declarations(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in CSS_DECLARATION_PATTERN.finditer(text):
        key = str(match.group(1)).strip().lower()
        value = str(match.group(2)).strip()
        if key and value:
            result[key] = value
    return result


def parse_border_shorthand(value: str) -> tuple[str | None, str | None, str | None]:
    text = str(value).strip()
    if not text:
        return None, None, None
    if re.match(r'^border(?:-(?:top|right|bottom|left))?\s*:', text, re.IGNORECASE):
        text = text.split(':', 1)[1].strip()
    text = text.removesuffix(';').strip()
    match = re.match(r'^(\S+)\s+(\S+)\s+(.+)$', text)
    if not match:
        return None, None, None
    width = str(match.group(1)).strip()
    style = str(match.group(2)).strip()
    color = str(match.group(3)).strip()
    return width or None, style or None, color or None


def parse_measure_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text or text.endswith('%'):
        return None
    if text.endswith('px'):
        text = text[:-2].strip()
    try:
        return float(text)
    except ValueError:
        return None
def _format_qss_color(color: QColor) -> str:
    return normalize_color_or_raw(color)
