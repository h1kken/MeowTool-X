from __future__ import annotations

from pathlib import Path

from src.theme.paths import PATH_THEMES_SOURCE, PATH_THEMES_USER
from src.theme.storage.io import SUPPORTED_THEME_EXTENSIONS, is_theme_file


def resolve_theme_path(theme_name: str) -> Path | None:
    value = theme_name.strip()
    if not value:
        return None

    raw = Path(value)
    candidates: list[Path] = []

    if raw.exists() and is_theme_file(raw):
        candidates.append(raw)
    if raw.is_absolute() and raw.is_file():
        candidates.append(raw)
    if raw.suffix.lower() in SUPPORTED_THEME_EXTENSIONS:
        candidates.append(PATH_THEMES_USER / raw.name)
        candidates.append(PATH_THEMES_SOURCE / raw.name)
    else:
        for extension in SUPPORTED_THEME_EXTENSIONS:
            candidates.append(PATH_THEMES_USER / f'{value}{extension}')
            candidates.append(PATH_THEMES_SOURCE / f'{value}{extension}')

    for candidate in candidates:
        if is_theme_file(candidate):
            return candidate
    return None
