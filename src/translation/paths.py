from __future__ import annotations

from src.app.paths import PATH_SETTINGS, PATH_SRC

PATH_TRANSLATIONS_SOURCE = PATH_SRC / 'translation' / 'translations'
PATH_TRANSLATIONS_USER = PATH_SETTINGS / 'Translations'


__all__ = (
    'PATH_TRANSLATIONS_SOURCE',
    'PATH_TRANSLATIONS_USER',
)

