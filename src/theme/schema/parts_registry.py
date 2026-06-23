from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, cast


@dataclass(frozen=True)
class PartsFieldSpec:
    key: str
    label: str
    placeholder: str
    group_key: str
    group_title: str
    path: tuple[str, ...]
    value_kind: str = 'string'
    minimum: int | None = None
    animation_property: str | None = None


PARTS_FIELD_SPECS: tuple[PartsFieldSpec, ...] = (
    PartsFieldSpec(
        'parts_groove_background_color',
        'Slider Groove Background',
        '#2a2d36',
        'slider',
        'Slider',
        ('groove', 'background', 'color'),
        animation_property='parts.groove.background.color',
    ),
    PartsFieldSpec(
        'parts_groove_border_width',
        'Slider Groove Border Width',
        '1px',
        'slider',
        'Slider',
        ('groove', 'border', 'width'),
    ),
    PartsFieldSpec(
        'parts_groove_border_style',
        'Slider Groove Border Style',
        'solid',
        'slider',
        'Slider',
        ('groove', 'border', 'style'),
    ),
    PartsFieldSpec(
        'parts_groove_border_color',
        'Slider Groove Border Color',
        '#2D3A4B',
        'slider',
        'Slider',
        ('groove', 'border', 'color'),
        animation_property='parts.groove.border.color',
    ),
    PartsFieldSpec(
        'parts_groove_border_radius',
        'Slider Groove Border Radius',
        '999px',
        'slider',
        'Slider',
        ('groove', 'border', 'radius'),
    ),
    PartsFieldSpec(
        'parts_groove_size',
        'Slider Groove Size',
        '6px',
        'slider',
        'Slider',
        ('groove', 'size'),
        animation_property='parts.groove.size',
    ),
    PartsFieldSpec(
        'parts_sub_page_background_color',
        'Slider Filled Background',
        '#6DAAFF',
        'slider',
        'Slider',
        ('sub_page', 'background', 'color'),
        animation_property='parts.sub_page.background.color',
    ),
    PartsFieldSpec(
        'parts_sub_page_border_width',
        'Slider Filled Border Width',
        '0px',
        'slider',
        'Slider',
        ('sub_page', 'border', 'width'),
    ),
    PartsFieldSpec(
        'parts_sub_page_border_style',
        'Slider Filled Border Style',
        'none',
        'slider',
        'Slider',
        ('sub_page', 'border', 'style'),
    ),
    PartsFieldSpec(
        'parts_sub_page_border_color',
        'Slider Filled Border Color',
        '#6DAAFF',
        'slider',
        'Slider',
        ('sub_page', 'border', 'color'),
        animation_property='parts.sub_page.border.color',
    ),
    PartsFieldSpec(
        'parts_sub_page_border_radius',
        'Slider Filled Border Radius',
        '999px',
        'slider',
        'Slider',
        ('sub_page', 'border', 'radius'),
    ),
    PartsFieldSpec(
        'parts_add_page_background_color',
        'Slider Empty Background',
        '#2a2d36',
        'slider',
        'Slider',
        ('add_page', 'background', 'color'),
        animation_property='parts.add_page.background.color',
    ),
    PartsFieldSpec(
        'parts_add_page_border_width',
        'Slider Empty Border Width',
        '0px',
        'slider',
        'Slider',
        ('add_page', 'border', 'width'),
    ),
    PartsFieldSpec(
        'parts_add_page_border_style',
        'Slider Empty Border Style',
        'none',
        'slider',
        'Slider',
        ('add_page', 'border', 'style'),
    ),
    PartsFieldSpec(
        'parts_add_page_border_color',
        'Slider Empty Border Color',
        '#2a2d36',
        'slider',
        'Slider',
        ('add_page', 'border', 'color'),
        animation_property='parts.add_page.border.color',
    ),
    PartsFieldSpec(
        'parts_add_page_border_radius',
        'Slider Empty Border Radius',
        '999px',
        'slider',
        'Slider',
        ('add_page', 'border', 'radius'),
    ),
    PartsFieldSpec(
        'parts_handle_background_color',
        'Slider Handle Background',
        '#ffffff',
        'slider',
        'Slider',
        ('handle', 'background', 'color'),
        animation_property='parts.handle.background.color',
    ),
    PartsFieldSpec(
        'parts_handle_border_width',
        'Slider Handle Border Width',
        '0px',
        'slider',
        'Slider',
        ('handle', 'border', 'width'),
    ),
    PartsFieldSpec(
        'parts_handle_border_style',
        'Slider Handle Border Style',
        'none',
        'slider',
        'Slider',
        ('handle', 'border', 'style'),
    ),
    PartsFieldSpec(
        'parts_handle_border_color',
        'Slider Handle Border Color',
        '#ffffff',
        'slider',
        'Slider',
        ('handle', 'border', 'color'),
        animation_property='parts.handle.border.color',
    ),
    PartsFieldSpec(
        'parts_handle_border_radius',
        'Slider Handle Border Radius',
        '999px',
        'slider',
        'Slider',
        ('handle', 'border', 'radius'),
    ),
    PartsFieldSpec(
        'parts_handle_width',
        'Slider Handle Width',
        '14px',
        'slider',
        'Slider',
        ('handle', 'width'),
        animation_property='parts.handle.width',
    ),
    PartsFieldSpec(
        'parts_handle_height',
        'Slider Handle Height',
        '14px',
        'slider',
        'Slider',
        ('handle', 'height'),
        animation_property='parts.handle.height',
    ),
    PartsFieldSpec(
        'parts_handle_margin',
        'Slider Handle Margin',
        '-4px 0 -4px 0',
        'slider',
        'Slider',
        ('handle', 'margin'),
    ),
    PartsFieldSpec(
        'parts_track_checked_color',
        'Switch Checked Color',
        '#6DAAFF',
        'switch',
        'Switch',
        ('track', 'checked', 'color'),
    ),
    PartsFieldSpec(
        'parts_track_unchecked_color',
        'Switch Unchecked Color',
        '#FFFFFF',
        'switch',
        'Switch',
        ('track', 'unchecked', 'color'),
    ),
    PartsFieldSpec(
        'parts_handle_color',
        'Switch Handle Color',
        '#000000',
        'switch',
        'Switch',
        ('handle', 'color'),
    ),
    PartsFieldSpec(
        'parts_handle_checked_color',
        'Switch Checked Handle Color',
        '#000000',
        'switch',
        'Switch',
        ('handle', 'checked', 'color'),
    ),
    PartsFieldSpec(
        'parts_handle_unchecked_color',
        'Switch Unchecked Handle Color',
        '#000000',
        'switch',
        'Switch',
        ('handle', 'unchecked', 'color'),
    ),
    PartsFieldSpec(
        'parts_size_width',
        'Switch Width',
        '40',
        'switch',
        'Switch',
        ('size', 'width'),
        value_kind='int',
        minimum=1,
    ),
    PartsFieldSpec(
        'parts_size_height',
        'Switch Height',
        '20',
        'switch',
        'Switch',
        ('size', 'height'),
        value_kind='int',
        minimum=1,
    ),
    PartsFieldSpec(
        'parts_layout_margin',
        'Switch Margin',
        '3',
        'switch',
        'Switch',
        ('layout', 'margin'),
        value_kind='int',
        minimum=0,
    ),
    PartsFieldSpec(
        'parts_combo_button_background_color',
        'Combo Button Background',
        'transparent',
        'combo',
        'ComboBox',
        ('button', 'background', 'color'),
        animation_property='parts.button.background.color',
    ),
    PartsFieldSpec(
        'parts_combo_button_border_width',
        'Combo Button Border Width',
        '0px',
        'combo',
        'ComboBox',
        ('button', 'border', 'width'),
    ),
    PartsFieldSpec(
        'parts_combo_button_border_style',
        'Combo Button Border Style',
        'solid',
        'combo',
        'ComboBox',
        ('button', 'border', 'style'),
    ),
    PartsFieldSpec(
        'parts_combo_button_border_color',
        'Combo Button Border Color',
        'transparent',
        'combo',
        'ComboBox',
        ('button', 'border', 'color'),
    ),
    PartsFieldSpec(
        'parts_combo_button_border_radius',
        'Combo Button Border Radius',
        '0px',
        'combo',
        'ComboBox',
        ('button', 'border', 'radius'),
    ),
    PartsFieldSpec(
        'parts_combo_button_width',
        'Combo Button Width',
        '18',
        'combo',
        'ComboBox',
        ('button', 'width'),
        value_kind='int',
        minimum=0,
    ),
    PartsFieldSpec(
        'parts_combo_icon_color',
        'Combo Icon Color',
        '#4d3d4f',
        'combo',
        'ComboBox',
        ('icon', 'color'),
        animation_property='parts.icon.color',
    ),
    PartsFieldSpec(
        'parts_combo_icon_size',
        'Combo Icon Size',
        '7',
        'combo',
        'ComboBox',
        ('icon', 'size'),
        value_kind='int',
        minimum=0,
    ),
    PartsFieldSpec(
        'parts_halo_color',
        'Ring Halo Color',
        'rgba(255, 153, 214, 0.13)',
        'ring',
        'Ring',
        ('halo', 'color'),
        animation_property='parts.halo.color',
    ),
    PartsFieldSpec(
        'parts_track_color',
        'Ring Track Color',
        '#2b2f3d',
        'ring',
        'Ring',
        ('track', 'color'),
        animation_property='parts.track.color',
    ),
    PartsFieldSpec(
        'parts_progress_color',
        'Ring Progress Color',
        '#ff8ac6',
        'ring',
        'Ring',
        ('progress', 'color'),
        animation_property='parts.progress.color',
    ),
    PartsFieldSpec(
        'parts_inner_color',
        'Ring Inner Color',
        '#111521',
        'ring',
        'Ring',
        ('inner', 'color'),
        animation_property='parts.inner.color',
    ),
    PartsFieldSpec(
        'parts_inner_glow_color',
        'Ring Inner Glow Color',
        'rgba(255, 255, 255, 0.04)',
        'ring',
        'Ring',
        ('inner', 'glow_color'),
    ),
    PartsFieldSpec(
        'parts_value_color',
        'Ring Value Color',
        '#f6f8ff',
        'ring',
        'Ring',
        ('value', 'color'),
        animation_property='parts.value.color',
    ),
    PartsFieldSpec(
        'parts_icon_source',
        'Ring Icon Source',
        'assets/icons/app/meowtool-x-icon.png',
        'ring',
        'Ring',
        ('icon', 'source'),
    ),
)
PARTS_GROUP_FIELD_KEYS: dict[str, tuple[str, ...]] = {}
_parts_group_titles: dict[str, str] = {}
for _spec in PARTS_FIELD_SPECS:
    PARTS_GROUP_FIELD_KEYS.setdefault(_spec.group_key, tuple())
    PARTS_GROUP_FIELD_KEYS[_spec.group_key] = (*PARTS_GROUP_FIELD_KEYS[_spec.group_key], _spec.key)
    _parts_group_titles.setdefault(_spec.group_key, _spec.group_title)

PARTS_FIELD_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = tuple(
    (group_key, _parts_group_titles[group_key], field_keys)
        for group_key, field_keys in PARTS_GROUP_FIELD_KEYS.items()
)
PARTS_FIELD_DEFS: tuple[tuple[str, str, str], ...] = tuple(
    (spec.key, spec.label, spec.placeholder)
        for spec in PARTS_FIELD_SPECS
)
PARTS_ANIMATION_PROPERTIES: tuple[str, ...] = tuple(
    dict.fromkeys(
        spec.animation_property
            for spec in PARTS_FIELD_SPECS
                if isinstance(spec.animation_property, str) and spec.animation_property.strip()
    )
)


def _nested_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    if not path:
        return data

    value = data.get(path[0])
    if len(path) == 1:
        return value
    if not isinstance(value, dict):
        return None
    return _nested_get(cast(dict[str, Any], value), path[1:])


def _nested_set(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current: dict[str, Any] = data
    for key in path[:-1]:
        node: object = current.get(key)
        if not isinstance(node, dict):
            node = {}
            current[key] = node
        current = cast(dict[str, Any], node)
    current[path[-1]] = value


def extract_parts_field_values(style: dict[str, Any]) -> dict[str, Any]:
    raw_parts = style.get('parts')
    parts: dict[str, Any] = cast(dict[str, Any], raw_parts) if isinstance(raw_parts, dict) else {}
    values: dict[str, Any] = {}
    for spec in PARTS_FIELD_SPECS:
        values[spec.key] = _nested_get(parts, spec.path)
    return values


def build_parts_style_from_field_values(
    field_values: Mapping[str, Any],
    *,
    parse_int: Callable[[str], int | None],
) -> dict[str, Any]:
    parts: dict[str, Any] = {}
    for spec in PARTS_FIELD_SPECS:
        raw = field_values.get(spec.key)
        if spec.value_kind == 'int':
            text = str(raw).strip() if raw is not None else ''
            if not text:
                continue
            parsed = parse_int(text)
            if parsed is None:
                continue
            if spec.minimum is not None and parsed < spec.minimum:
                continue
            _nested_set(parts, spec.path, parsed)
            continue

        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        _nested_set(parts, spec.path, text)
    return parts
