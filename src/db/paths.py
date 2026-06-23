from __future__ import annotations

from src.app.paths import PATH_SETTINGS

PATH_DATABASES = PATH_SETTINGS / 'Database'
PATH_APP_DATABASE = PATH_DATABASES / 'meowtool-x.sqlite3'


__all__ = (
    'PATH_DATABASES',
    'PATH_APP_DATABASE',
)

