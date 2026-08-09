from __future__ import annotations

import typing as t

from pathlib import Path
import json5

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES
from src.ui.theme.parser import ThemeMap
from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.config import Config


type LoadedTheme = tuple[Path, ThemeMap]


def read(path: Path) -> ThemeMap:
    text = path.read_text(encoding='utf-8')
    data: object = t.cast(object, json5.loads(text)) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f'Theme root must be an object: {path}')
    return t.cast(ThemeMap, data)


def load(config: Config, name: str | None = None) -> LoadedTheme | None:
    theme_path = _resolve_path(str(config.get('General>Theme')) if name is None else name)

    for path in dict.fromkeys((theme_path, PATH_DEFAULT_THEME)):
        if path is None:
            continue
        try:
            return path, read(path)
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.warning(f'Can\'t load theme \'{path}\'. Error: {e}')
    return None


def _resolve_path(name: str) -> Path | None:
    for directory in (PATH_THEMES, PATH_THEMES_SRC):
        path = directory / name
        if _is_theme_file(path):
            return path
    return None
