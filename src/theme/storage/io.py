from __future__ import annotations

from pathlib import Path
from typing import Any

import json5

from src.exceptions.json import NotADictionaryError
from src.theme.storage.serialization import format_theme_json
from src.utils.logging import logger

SUPPORTED_THEME_EXTENSIONS: tuple[str, ...] = ('.json5', '.json')
DEFAULT_USER_THEME_EXTENSION = '.json5'


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


def load_theme_payload(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding='utf-8')
        if not text.strip():
            return {}

        data = json5.loads(text)

        if not isinstance(data, dict):
            raise NotADictionaryError

        return data
    except FileNotFoundError:
        logger.warning(f'Theme file not found: {path}')
    except NotADictionaryError:
        logger.debug(f'Theme file does not contain a dictionary payload: {path}')
    except ValueError as e:
        logger.debug(f'Cannot decode theme JSON5 in {path}: {e}')
    except UnicodeDecodeError:
        logger.debug(f'Cannot decode theme unicode in {path}')
    except Exception:
        logger.exception(f'Error while loading theme {path}')
    return {}


def write_theme_payload(path: Path, payload: dict[str, Any]) -> None:
    existing_text = None
    if path.suffix.lower() == '.json5' and path.exists():
        try:
            existing_text = path.read_text(encoding='utf-8')
        except OSError:
            existing_text = None
    path.write_text(format_theme_json(payload, existing_text=existing_text), encoding='utf-8')


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
