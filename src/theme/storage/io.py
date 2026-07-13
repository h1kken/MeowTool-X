from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import json5

from src.utils.logging import logger

SUPPORTED_THEME_EXTENSIONS: tuple[str, ...] = ('.json5', '.json')
DEFAULT_USER_THEME_EXTENSION = '.json5'


class ThemeFileError(ValueError):
    pass


def is_theme_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_THEME_EXTENSIONS


def iter_theme_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for extension in reversed(SUPPORTED_THEME_EXTENSIONS):
        files.extend(
            path
            for path in root.glob(f'*{extension}')
            if path.is_file()
        )
    return files


def read_theme_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    data: object = cast(object, json5.loads(text)) if text.strip() else {}
    if not isinstance(data, dict):
        raise ThemeFileError(f'Theme root must be an object: {path}')
    return cast(dict[str, Any], data)


def load_theme_payload(path: Path) -> dict[str, Any]:
    try:
        return read_theme_payload(path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        logger.warning(f"Can't load theme '{path}'. Error: {error}")
    return {}


def write_theme_payload(path: Path, payload: dict[str, Any]) -> None:
    text = json5.dumps(payload, ensure_ascii=False, indent=2, quote_keys=True)
    path.write_text(f'{text}\n', encoding='utf-8')


def normalize_theme_name(value: str) -> str:
    name = Path(str(value or '').strip()).stem.strip()
    return name


def theme_output_path(directory: Path, name: str, *, preferred_suffix: str | None = None) -> Path:
    suffix = str(preferred_suffix or DEFAULT_USER_THEME_EXTENSION).strip().lower()
    if suffix not in SUPPORTED_THEME_EXTENSIONS:
        suffix = DEFAULT_USER_THEME_EXTENSION
    return directory / f'{name}{suffix}'


def find_theme_file_by_name(directory: Path, name: str) -> Path | None:
    normalized = normalize_theme_name(name)
    if not normalized:
        return None

    for path in iter_theme_files(directory):
        if path.stem == normalized:
            return path
    return None
