from __future__ import annotations

from pathlib import Path
import typing as t

import json5

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.theme.parser import ThemeMap
from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.config.manager import Config

SUPPORTED_EXTENSIONS: tuple[str, ...] = ('.json5', '.json')
DEFAULT_EXTENSION = '.json5'
type LoadedTheme = tuple[Path, ThemeMap]


def _is_theme_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    paths = tuple(root.iterdir())
    return [
        path
        for extension in reversed(SUPPORTED_EXTENSIONS)
        for path in paths
        if path.suffix.lower() == extension and path.is_file()
    ]


def read(path: Path) -> ThemeMap:
    text = path.read_text(encoding='utf-8')
    data: object = t.cast(object, json5.loads(text)) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f'Theme root must be an object: {path}')
    return t.cast(ThemeMap, data)


def read_safe(path: Path) -> ThemeMap:
    try:
        return read(path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        logger.warning(f"Can't load theme '{path}'. Error: {error}")
    return {}


def write(path: Path, payload: ThemeMap) -> None:
    text = json5.dumps(payload, ensure_ascii=False, indent=2, quote_keys=True)
    path.write_text(f'{text}\n', encoding='utf-8')


def output_path(directory: Path, name: str, *, preferred_suffix: str | None = None) -> Path:
    suffix = str(preferred_suffix or DEFAULT_EXTENSION).strip().lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = DEFAULT_EXTENSION
    return directory / f'{name}{suffix}'


def find(directory: Path, name: str) -> Path | None:
    for path in iter_files(directory):
        if path.stem == name:
            return path
    return None


def load(config: Config, name: str | None = None) -> LoadedTheme | None:
    theme_path = _resolve_path(str(config.get("General>Theme")) if name is None else name)

    for path in dict.fromkeys((theme_path, PATH_DEFAULT_THEME)):
        if path is None:
            continue
        try:
            return path, read(path)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            logger.warning(f"Can't load theme '{path}'. Error: {error}")
    return None


def _resolve_path(name: str) -> Path | None:
    for directory in (PATH_THEMES_USER, PATH_THEMES_SRC):
        path = directory / name
        if _is_theme_file(path):
            return path
    return None
