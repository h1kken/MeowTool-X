from __future__ import annotations

from src.app.paths import PATH_SETTINGS, PATH_SRC

PATH_THEMES_SOURCE = PATH_SRC / 'theme' / 'themes'
PATH_THEMES_USER = PATH_SETTINGS / 'Themes'
PATH_DEFAULT_THEME = PATH_THEMES_SOURCE / 'pink.json'
PATH_FONTS = PATH_SETTINGS / 'Fonts'


__all__ = (
    'PATH_THEMES_SOURCE',
    'PATH_THEMES_USER',
    'PATH_DEFAULT_THEME',
    'PATH_FONTS',
)

