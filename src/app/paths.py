from __future__ import annotations

import os
import sys
from PySide6.QtCore import QStandardPaths
from pathlib import Path

from .constants import PROGRAM_NAME


def _find_bundle_root() -> Path:
    bundle_path = getattr(sys, '_MEIPASS', None)
    if isinstance(bundle_path, str):
        return Path(bundle_path).resolve()

    for path in Path(__file__).resolve().parents:
        if path.name == 'src':
            return path.parent
        
    return Path.cwd().resolve()


def _find_app_root(bundle_root: Path) -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return bundle_root


### roots
PATH_ROOT = _find_bundle_root()
PATH_APP_ROOT = _find_app_root(PATH_ROOT)

PATH_SYSTEM_DRIVE = Path(os.environ['SystemDrive'])

PATH_APPDATA = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
PATH_APPDATA_APP_DIR = PATH_APPDATA / PROGRAM_NAME

PATH_LOCALAPPDATA = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))

### src
PATH_SRC = PATH_ROOT / 'src'

## loader
PATH_DEFAULT_LOADER = PATH_APPDATA_APP_DIR / 'loader.txt'

## data
PATH_DATA_SRC = PATH_SRC / 'data'
PATH_COUNTRY_CODES = PATH_DATA_SRC / 'country_codes.json'

## assets
PATH_ASSETS_SRC = PATH_SRC / 'assets'

# icons
PATH_ICONS_SRC = PATH_ASSETS_SRC / 'icons'
PATH_CONTAINER_ARROW_ICON = PATH_ICONS_SRC / 'container_arrow.svg'
PATH_FOLDER_ICON = PATH_ICONS_SRC / 'folder.svg'

PATH_HEADER_ICONS_SRC = PATH_ICONS_SRC / 'header'

PATH_SIDEBAR_ICONS_SRC = PATH_ICONS_SRC / 'sidebar-buttons'

PATH_APP_ICONS_SRC = PATH_ICONS_SRC / 'app'
PATH_APP_ICON = PATH_APP_ICONS_SRC / 'meowtool-x-icon.png'
PATH_APP_LABEL = PATH_APP_ICONS_SRC / 'meowtool-x-label.png'

## themes
PATH_THEMES = PATH_APPDATA_APP_DIR / 'Themes'
PATH_DEFAULT_THEME = PATH_THEMES / 'default.json5'

## translations
PATH_TRANSLATIONS_SRC = PATH_SRC / 'translation' / 'translations'
PATH_DEFAULT_TRANSLATION = PATH_TRANSLATIONS_SRC / 'en_US.axis'

PATH_TRANSLATIONS_USER = PATH_APPDATA_APP_DIR / 'Translations'

## configs
PATH_CONFIGS = PATH_APPDATA_APP_DIR / 'Configs'
PATH_DEFAULT_CONFIG = PATH_CONFIGS / 'default.txt'

### work data
PATH_LOGS = PATH_APPDATA_APP_DIR / 'Logs'

PATH_CACHE = PATH_APPDATA_APP_DIR / 'Cache'
PATH_CACHE_AVATARS = PATH_CACHE / 'Avatars'

PATH_DATABASES = PATH_APPDATA_APP_DIR / 'Databases'

PATH_DATABASES_ROBLOX = PATH_DATABASES / 'Roblox'
PATH_ROBLOX_COOKIE_CHECKER_DB = PATH_DATABASES_ROBLOX / 'CookieChecker.db'
PATH_ROBLOX_COOKIE_SORTER_DB = PATH_DATABASES_ROBLOX / 'CookieSorter.db'
PATH_ROBLOX_COOKIE_REFRESHER_DB = PATH_DATABASES_ROBLOX / 'CookieRefresher.db'

### roblox
PATH_FISHSTRAP = PATH_LOCALAPPDATA / 'Fishstrap' / 'Fishstrap.exe'
PATH_BLOXSTRAP = PATH_LOCALAPPDATA / 'Bloxstrap' / 'Bloxstrap.exe'
PATH_ROBLOXPLAYERBETA = PATH_SYSTEM_DRIVE / 'Program Files (x86)' / 'Roblox' / 'Versions'


__all__ = [name for name in globals() if name.startswith('PATH_')]
