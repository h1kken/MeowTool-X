import os
import sys
from pathlib import Path


def _find_bundle_root() -> Path:
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS).resolve()

    parents = Path(__file__).resolve().parents
    for idx, path in enumerate(parents):
        if path.name == 'src':
            return parents[idx + 1]

    return Path.cwd().resolve()


def _find_app_root(bundle_root: Path) -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return bundle_root


ROOT = _find_bundle_root()
APP_ROOT = _find_app_root(ROOT)

LOCAL_APPDATA = Path(os.environ['LOCALAPPDATA'])
SYSTEM_DRIVE = Path(os.environ['SystemDrive'])

PATH_SRC = ROOT / 'src'
PATH_ASSETS = PATH_SRC / 'assets'
PATH_ICONS = PATH_ASSETS / 'icons'
PATH_SIDEBAR_ICONS = PATH_ICONS / "sidebar-buttons"
PATH_CONTAINER_ARROW_ICON = PATH_ICONS / 'container_arrow.svg'
PATH_HEADER_ICONS = PATH_ICONS / 'header'
PATH_APP_ICON = PATH_ICONS / 'app' / 'meowtool-x-icon.png'
PATH_APP_LABEL = PATH_ICONS / 'app' / 'meowtool-x-label.png'

PATH_TRANSLATIONS_USER = APP_ROOT / 'Settings' / 'Translations'
PATH_TRANSLATIONS_SOURCE = PATH_SRC / 'translation' / 'translations'

PATH_THEMES_USER = APP_ROOT / 'Settings' / 'Themes'
PATH_THEMES_SOURCE = PATH_SRC / 'theme' / 'themes'

PATH_FONTS = APP_ROOT / 'Settings' / 'Fonts'

PATH_CONFIGS = APP_ROOT / 'Settings' / 'Configs'

PATH_FISHSTRAP = LOCAL_APPDATA / 'Fishstrap' / 'Fishstrap.exe'
PATH_BLOXSTRAP = LOCAL_APPDATA / 'Bloxstrap' / 'Bloxstrap.exe'
PATH_ROBLOXPLAYERBETA = SYSTEM_DRIVE / 'Program Files (x86)' / 'Roblox' / 'Versions'


__all__ = [name for name in globals() if name.isupper()]
