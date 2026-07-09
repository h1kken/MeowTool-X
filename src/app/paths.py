from __future__ import annotations

import os
import sys
from pathlib import Path

from src.app.constants import APP_DIRNAME

def _find_bundle_root() -> Path:
    bundle_path = getattr(sys, '_MEIPASS', None)
    if isinstance(bundle_path, str):
        return Path(bundle_path).resolve()

    parents = Path(__file__).resolve().parents
    for idx, path in enumerate(parents):
        if path.name == 'src':
            return parents[idx + 1]
    return Path.cwd().resolve()


def _find_app_root(bundle_root: Path) -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return bundle_root


### roots
PATH_ROOT = _find_bundle_root()
PATH_APP_ROOT = _find_app_root(PATH_ROOT)

PATH_SYSTEM_DRIVE = Path(os.environ['SystemDrive'])

PATH_APPDATA = Path(os.environ['APPDATA'])
PATH_APPDATA_APP_DIR = PATH_APPDATA / APP_DIRNAME

PATH_LOCALAPPDATA = Path(os.environ['LOCALAPPDATA'])

### src
PATH_SRC = PATH_ROOT / 'src'

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
PATH_THEMES_SRC = PATH_SRC / 'theme' / 'themes'
PATH_DEFAULT_THEME = PATH_THEMES_SRC / 'pink.json5'

PATH_THEMES_USER = PATH_APPDATA_APP_DIR / 'Themes'

## translations
PATH_TRANSLATIONS_SRC = PATH_SRC / 'translation' / 'translations'
PATH_DEFAULT_TRANSLATION = PATH_TRANSLATIONS_SRC / 'en_US.axis'

PATH_TRANSLATIONS_USER = PATH_APPDATA_APP_DIR / 'Translations'

### other user data
PATH_CONFIGS_USER = PATH_APPDATA_APP_DIR / 'Configs'
PATH_DEFAULT_CONFIG = PATH_CONFIGS_USER / 'default.txt'
PATH_DEFAULT_CONFIG_LOADER = PATH_CONFIGS_USER / '.loader.txt'

### work data
PATH_LOGS_USER = PATH_APPDATA_APP_DIR / 'Logs'
PATH_CACHE_USER = PATH_APPDATA_APP_DIR / 'Cache'
PATH_FONTS_USER = PATH_APPDATA_APP_DIR / 'Fonts'

PATH_DATABASES_USER = PATH_APPDATA_APP_DIR / 'Databases'

PATH_DATABASES_ROBLOX_USER = PATH_DATABASES_USER / 'Roblox'
PATH_ROBLOX_COOKIE_CHECKER_DB = PATH_DATABASES_ROBLOX_USER / 'cookie-checker.db'
PATH_ROBLOX_COOKIE_SORTER_DB = PATH_DATABASES_ROBLOX_USER / 'cookie-sorter.db'
PATH_ROBLOX_COOKIE_REFRESHER_DB = PATH_DATABASES_ROBLOX_USER / 'cookie-refresher.db'

### roblox
PATH_FISHSTRAP = PATH_LOCALAPPDATA / 'Fishstrap' / 'Fishstrap.exe'
PATH_BLOXSTRAP = PATH_LOCALAPPDATA / 'Bloxstrap' / 'Bloxstrap.exe'
PATH_ROBLOXPLAYERBETA = PATH_SYSTEM_DRIVE / 'Program Files (x86)' / 'Roblox' / 'Versions'


__all__ = tuple(name for name in globals() if name.startswith('PATH_'))
