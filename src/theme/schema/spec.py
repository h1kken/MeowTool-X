from __future__ import annotations

from copy import deepcopy
from typing import Any

TEXT_ALIGNMENT_VALUES: tuple[str, ...] = (
    'left',
    'right',
    'top',
    'bottom',
    'center',
    'hcenter',
    'vcenter',
    'middle',
    'justify',
)

LAYOUT_ALIGNMENT_VALUES: tuple[str, ...] = TEXT_ALIGNMENT_VALUES

THEME_STYLE_SPEC: dict[str, Any] = {
    'common_sections': {
        'clear': 'clear local widget stylesheet before applying theme rules',
        'rainbow': 'enable/disable runtime rainbow border targeting',
        'background': (
            'color',
            'image'
        ),
        'text': (
            'color',
            'align',
            'align.focused',
            'align.unfocused',
            'spacing',
            'letter_spacing',
            'letter-spacing',
            'font',
            'shadow',
            'border',
            'icon'
        ),
        'padding': 'inner widget content padding',
        'border': (
            'width',
            'style',
            'color',
            'radius',
            'top',
            'right',
            'bottom',
            'left',
            'top_width',
            'top_style',
            'top_color',
            'right_width',
            'right_style',
            'right_color',
            'bottom_width',
            'bottom_style',
            'bottom_color',
            'left_width',
            'left_style',
            'left_color',
        ),
        'layout': (
            'margin',
            'spacing',
            'align',
            'justify'
        ),
        'geometry': (
            'min_width',
            'max_width',
            'min_height',
            'max_height',
            'fixed_width',
            'fixed_height',
            'width',
            'height',
        ),
        'dropdown': (
            'background',
            'text',
            'border',
            'selection'
        ),
        'items': (
            'background',
            'text',
            'border',
            'padding',
            'selection'
        ),
        'media': (
            'source',
            'fit',
            'icon'
        ),
        'parts': 'custom-widget specific',
        'animations': 'runtime animation specs',
        'qss': 'raw Qt stylesheet passthrough',
    },
    'text_align_values': TEXT_ALIGNMENT_VALUES,
    'layout_align_values': LAYOUT_ALIGNMENT_VALUES,
    'layout_justify_values': ('start', 'center', 'end', 'space_between'),
}


def theme_style_spec() -> dict[str, Any]:
    return deepcopy(THEME_STYLE_SPEC)
