from __future__ import annotations

import os
import sys
from pathlib import Path


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


SYSTEM_DRIVE = Path(os.environ['SystemDrive'])
LOCAL_APPDATA = Path(os.environ['LOCALAPPDATA'])

PATH_ROOT = _find_bundle_root()
PATH_APP_ROOT = _find_app_root(PATH_ROOT)
PATH_SRC = PATH_ROOT / 'src'
PATH_SETTINGS = PATH_APP_ROOT / 'Settings'
PATH_DATA = PATH_SRC / 'data'
PATH_ASSETS = PATH_SRC / 'assets'
PATH_LOGS = LOCAL_APPDATA / 'MeowTool' / 'Logs'


__all__ = (
    'SYSTEM_DRIVE',
    'LOCAL_APPDATA',
    'PATH_ROOT',
    'PATH_APP_ROOT',
    'PATH_SRC',
    'PATH_SETTINGS',
    'PATH_DATA',
    'PATH_ASSETS',
    'PATH_LOGS',
)
