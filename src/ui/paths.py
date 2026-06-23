from __future__ import annotations

from src.app.paths import PATH_ASSETS

PATH_ICONS = PATH_ASSETS / 'icons'
PATH_SIDEBAR_ICONS = PATH_ICONS / 'sidebar-buttons'
PATH_CONTAINER_ARROW_ICON = PATH_ICONS / 'container_arrow.svg'
PATH_HEADER_ICONS = PATH_ICONS / 'header'
PATH_FOLDER_ICON = PATH_ICONS / 'folder.svg'
PATH_APP_ICON = PATH_ICONS / 'app' / 'meowtool-x-icon.png'
PATH_APP_LABEL = PATH_ICONS / 'app' / 'meowtool-x-label.png'


__all__ = (
    'PATH_ICONS',
    'PATH_SIDEBAR_ICONS',
    'PATH_CONTAINER_ARROW_ICON',
    'PATH_HEADER_ICONS',
    'PATH_FOLDER_ICON',
    'PATH_APP_ICON',
    'PATH_APP_LABEL',
)
