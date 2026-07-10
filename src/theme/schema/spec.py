from __future__ import annotations

from copy import deepcopy
from typing import Any

THEME_STYLE_SPEC: dict[str, Any] = {
    'common_sections': {
        'background': (
            'color',
            'image',
            'radius',
        ),
        'text': (
            'color',
            'font',
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
        'media': (
            'source',
        ),
        'animations': 'runtime animation specs',
        'qss': 'raw Qt stylesheet passthrough',
    },
}


def theme_style_spec() -> dict[str, Any]:
    return deepcopy(THEME_STYLE_SPEC)
