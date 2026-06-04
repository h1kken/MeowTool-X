# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).resolve().parent
icon_path = project_root / 'src' / 'assets' / 'icons' / 'app' / 'meowtool-x-icon.ico'

datas = [
    (str(project_root / 'src' / 'assets'), 'src/assets'),
    (str(project_root / 'src' / 'theme' / 'themes'), 'src/theme/themes'),
    (str(project_root / 'src' / 'translation' / 'translations'), 'src/translation/translations'),
]

hiddenimports = [
    'meowtool_native_http',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MeowTool-onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
