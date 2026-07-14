from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import json5

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.theme.parser import ThemeMap
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.config.manager import Config

SUPPORTED_EXTENSIONS: tuple[str, ...] = ('.json5', '.json')
DEFAULT_EXTENSION = '.json5'
type LoadedTheme = tuple[Path, ThemeMap]


def _is_theme_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for extension in reversed(SUPPORTED_EXTENSIONS):
        files.extend(
            path
            for path in root.glob(f'*{extension}')
            if path.is_file()
        )
    return files


def read(path: Path) -> ThemeMap:
    text = path.read_text(encoding='utf-8')
    data: object = cast(object, json5.loads(text)) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f'Theme root must be an object: {path}')
    return cast(ThemeMap, data)


def read_safe(path: Path) -> ThemeMap:
    try:
        return read(path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        logger.warning(f"Can't load theme '{path}'. Error: {error}")
    return {}


def write(path: Path, payload: ThemeMap) -> None:
    text = json5.dumps(payload, ensure_ascii=False, indent=2, quote_keys=True)
    path.write_text(f'{text}\n', encoding='utf-8')


def normalize_name(value: str) -> str:
    name = Path(str(value or '').strip()).stem.strip()
    return name


def output_path(directory: Path, name: str, *, preferred_suffix: str | None = None) -> Path:
    suffix = str(preferred_suffix or DEFAULT_EXTENSION).strip().lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = DEFAULT_EXTENSION
    return directory / f'{name}{suffix}'


def find(directory: Path, name: str) -> Path | None:
    normalized = normalize_name(name)
    if not normalized:
        return None

    for path in iter_files(directory):
        if path.stem == normalized:
            return path
    return None


def load(config: Config, name: str | None = None) -> LoadedTheme | None:
    requested = (
        str(config.get("General>Theme", default=PATH_DEFAULT_THEME.stem)).strip()
        if name is None
        else str(name).strip()
    )
    selected = _resolve(requested)

    for path in dict.fromkeys((selected, _default_path())):
        if path is None:
            continue
        try:
            return path, read(path)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            logger.warning(f"Can't load theme '{path}'. Error: {error}")
    return None


def _resolve(name: str) -> Path | None:
    raw = Path(str(name).strip())
    theme_name = raw.stem.strip()
    if not theme_name:
        return None

    suffixes = (
        (raw.suffix.lower(),)
        if raw.suffix.lower() in SUPPORTED_EXTENSIONS
        else SUPPORTED_EXTENSIONS
    )
    for suffix in suffixes:
        for directory in (PATH_THEMES_USER, PATH_THEMES_SRC):
            path = directory / f"{theme_name}{suffix}"
            if _is_theme_file(path):
                return path
    return None


def _default_path() -> Path:
    if _is_theme_file(PATH_DEFAULT_THEME):
        return PATH_DEFAULT_THEME
    for suffix in SUPPORTED_EXTENSIONS:
        candidate = PATH_THEMES_SRC / f"{PATH_DEFAULT_THEME.stem}{suffix}"
        if _is_theme_file(candidate):
            return candidate
    return PATH_DEFAULT_THEME
