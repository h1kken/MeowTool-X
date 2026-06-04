from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from src.theme.storage.io import SUPPORTED_THEME_EXTENSIONS, is_theme_file, load_theme_payload
from src.theme.schema.payload import resolve_theme_vars
from src.utils.constants import (
    DEFAULT_THEME,
    PATH_THEMES_SOURCE,
    PATH_THEMES_USER,
    ROOT,
)
from src.utils.preload import extract_preload_widget_rules


def resolve_theme_path(theme_name: str) -> Path | None:
    if not isinstance(theme_name, str):
        return None

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


def load_preload_theme(theme_name: str | None) -> dict[str, Any]:
    widgets: list[dict[str, Any]] = []

    if DEFAULT_THEME.exists():
        default_payload = load_theme_payload(DEFAULT_THEME)
        widgets.extend(_prepare_preload_widget_rules(default_payload, base_dir=DEFAULT_THEME.parent))

    selected_path = resolve_theme_path(str(theme_name or '').strip())
    if selected_path is not None and selected_path != DEFAULT_THEME:
        selected_payload = load_theme_payload(selected_path)
        widgets.extend(_prepare_preload_widget_rules(selected_payload, base_dir=selected_path.parent))

    return {'widgets': widgets}


def _prepare_preload_widget_rules(payload: Any, *, base_dir: Path | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    resolved_payload = resolve_theme_vars(payload)
    rules = extract_preload_widget_rules(resolved_payload.get('widgets'))
    return [
        _resolve_widget_rule_assets(rule, base_dir=base_dir)
        for rule in rules
    ]


def _resolve_widget_rule_assets(entry: dict[str, Any], *, base_dir: Path | None) -> dict[str, Any]:
    return _resolve_asset_values(deepcopy(entry), base_dir=base_dir)


def _resolve_asset_values(value: Any, *, base_dir: Path | None) -> Any:
    if isinstance(value, dict):
        resolved: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, str) and str(key) in {'source', 'image'}:
                resolved[str(key)] = _resolve_theme_asset_path(item, base_dir=base_dir)
                continue
            resolved[str(key)] = _resolve_asset_values(item, base_dir=base_dir)
        return resolved

    if isinstance(value, list):
        return [_resolve_asset_values(item, base_dir=base_dir) for item in value]

    return value


def _resolve_theme_asset_path(source: str, *, base_dir: Path | None = None) -> str:
    value = source.strip()
    if not value:
        return ''

    raw = Path(value).expanduser()
    candidates: list[Path] = [raw]
    if not raw.is_absolute():
        if base_dir is not None:
            candidates.insert(0, base_dir / raw)
        candidates.append(ROOT / raw)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    return value



def load_startup_screen_theme(theme_name: str | None) -> dict[str, Any]:
    return load_preload_theme(theme_name)
