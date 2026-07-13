from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.theme.storage.io import (
    SUPPORTED_THEME_EXTENSIONS,
    is_theme_file,
    read_theme_payload,
)
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.config.manager import Config

type LoadedTheme = tuple[Path, dict[str, Any]]


def resolve_theme_path(name: str) -> Path | None:
    raw = Path(str(name).strip())
    theme_name = raw.stem.strip()
    if not theme_name:
        return None

    suffixes = (
        (raw.suffix.lower(),)
        if raw.suffix.lower() in SUPPORTED_THEME_EXTENSIONS
        else SUPPORTED_THEME_EXTENSIONS
    )
    for suffix in suffixes:
        for directory in (PATH_THEMES_USER, PATH_THEMES_SRC):
            path = directory / f"{theme_name}{suffix}"
            if is_theme_file(path):
                return path
    return None


def load_theme(config: Config, name: str | None = None) -> LoadedTheme | None:
    requested = (
        str(config.get("General>Theme", default=PATH_DEFAULT_THEME.stem)).strip()
        if name is None
        else str(name).strip()
    )
    selected = resolve_theme_path(requested)
    fallback = _default_theme_path()

    for path in dict.fromkeys((selected, fallback)):
        if path is None:
            continue
        try:
            return path, read_theme_payload(path)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            logger.warning(f"Can't load theme '{path}'. Error: {error}")

    return None


def _default_theme_path() -> Path:
    if is_theme_file(PATH_DEFAULT_THEME):
        return PATH_DEFAULT_THEME
    for suffix in SUPPORTED_THEME_EXTENSIONS:
        candidate = PATH_THEMES_SRC / f"{PATH_DEFAULT_THEME.stem}{suffix}"
        if is_theme_file(candidate):
            return candidate
    return PATH_DEFAULT_THEME
