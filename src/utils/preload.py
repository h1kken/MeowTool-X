from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from PySide6.QtGui import QColor

from src.theme.colors import to_qcolor
from src.translation import translator as t
from src.utils.constants import PRELOAD_DEFAULT_STAGE

_PRELOAD_TARGET_PREFIX = 'Preload_'
_PRELOAD_WINDOW_TARGET = 'Preload_Window'
_PRELOAD_SCREEN_TARGET = 'Preload_Screen'
_PRELOAD_STAGE_TEXT_KEYS = {
    'Preparing startup counters': 'PRELOAD_STAGE_PREPARING_STARTUP',
    'Configuring main window': 'PRELOAD_STAGE_CONFIGURING_MAIN_WINDOW',
    'Building interface shell': 'PRELOAD_STAGE_BUILDING_INTERFACE_SHELL',
    'Starting animation engine': 'PRELOAD_STAGE_STARTING_ANIMATION_ENGINE',
    'Starting theme engine': 'PRELOAD_STAGE_STARTING_THEME_ENGINE',
    'Applying current theme': 'PRELOAD_STAGE_APPLYING_CURRENT_THEME',
    'Prewarming Settings: Config and Theme': 'PRELOAD_STAGE_PREWARMING_SETTINGS_THEME',
    'Finalizing startup': 'PRELOAD_STAGE_FINALIZING_STARTUP',
}

_PRELOAD_STAGE_SPLIT_KEYS = {
    'Preparing startup counters': ('PRELOAD_ACTION_PREPARING', 'PRELOAD_TARGET_STARTUP_COUNTERS'),
    'Configuring main window': ('PRELOAD_ACTION_CONFIGURING', 'PRELOAD_TARGET_MAIN_WINDOW'),
    'Building interface shell': ('PRELOAD_ACTION_BUILDING', 'PRELOAD_TARGET_INTERFACE_SHELL'),
    'Starting animation engine': ('PRELOAD_ACTION_STARTING', 'PRELOAD_TARGET_ANIMATION_ENGINE'),
    'Starting theme engine': ('PRELOAD_ACTION_STARTING', 'PRELOAD_TARGET_THEME_ENGINE'),
    'Applying current theme': ('PRELOAD_ACTION_APPLYING', 'PRELOAD_TARGET_CURRENT_THEME'),
    'Prewarming Settings: Config and Theme': ('PRELOAD_ACTION_PREWARMING', 'PRELOAD_TARGET_SETTINGS_THEME'),
    'Finalizing startup': ('PRELOAD_ACTION_FINALIZING', 'PRELOAD_TARGET_STARTUP'),
}


def _tr(key: str, **kwargs) -> str:
    return t.tr(key, **kwargs)


def beautify_preload_target_name(value: str) -> str:
    text = value.strip().replace('_', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text or _tr('PRELOAD_TARGET_CURRENT')


def split_preload_stage_text(stage: str) -> tuple[str, str]:
    cleaned = stage.strip()
    if not cleaned:
        action_key, target_key = _PRELOAD_STAGE_SPLIT_KEYS[PRELOAD_DEFAULT_STAGE]
        return _tr(action_key), _tr(target_key)

    if cleaned in _PRELOAD_STAGE_SPLIT_KEYS:
        action_key, target_key = _PRELOAD_STAGE_SPLIT_KEYS[cleaned]
        return _tr(action_key), _tr(target_key)

    if cleaned.startswith('Loading page:'):
        page_name = cleaned.removeprefix('Loading page:').strip()
        return _tr('PRELOAD_ACTION_LOADING_PAGE'), beautify_preload_target_name(page_name)

    if cleaned.startswith('Loading settings:'):
        setting_name = cleaned.removeprefix('Loading settings:').strip()
        return _tr('PRELOAD_ACTION_LOADING_SETTINGS'), beautify_preload_target_name(setting_name)

    if cleaned.startswith('Prewarming settings:'):
        setting_name = cleaned.removeprefix('Prewarming settings:').strip()
        return _tr('PRELOAD_ACTION_PREWARMING_SETTINGS'), beautify_preload_target_name(setting_name)

    if cleaned.startswith('Prewarming '):
        name = cleaned.removeprefix('Prewarming ').strip()
        return _tr('PRELOAD_ACTION_PREWARMING'), beautify_preload_target_name(name)

    if cleaned.startswith('Creating '):
        name = cleaned.removeprefix('Creating ').strip()
        return _tr('PRELOAD_ACTION_CREATING'), beautify_preload_target_name(name)

    if cleaned.startswith('Bootstrapping '):
        program_name = cleaned.removeprefix('Bootstrapping ').strip()
        return _tr('PRELOAD_ACTION_BOOTSTRAPPING'), beautify_preload_target_name(program_name)

    if cleaned == 'Startup complete':
        return _tr('PRELOAD_ACTION_READY'), ''

    if cleaned.startswith('Dumping object tree:'):
        details = cleaned.removeprefix('Dumping object tree:').strip()
        target = details.rsplit('·', 1)[-1].strip() if '·' in details else details
        return _tr('PRELOAD_ACTION_INDEXING_OBJECT_TREE'), beautify_preload_target_name(target)

    return _tr('PRELOAD_ACTION_WORKING_ON'), cleaned


def format_preload_stage_text(stage: str) -> str:
    action, target = split_preload_stage_text(stage)
    if target:
        return f'{action}: {target}'
    return action


def format_preload_counter_with_label(step: int | float, total: int | float, label_key: str) -> str:
    safe_total = max(0, int(round(float(total))))
    safe_step = max(0, min(int(round(float(step))), safe_total if safe_total > 0 else int(round(float(step)))))
    return _tr(
        'PRELOAD_COUNTER_WITH_LABEL',
        current=safe_step,
        total=safe_total,
        label=_tr(label_key),
    )


def format_preload_counter_remaining(step: int | float, total: int | float) -> str:
    safe_total = max(1, int(round(float(total))))
    safe_step = max(0, min(int(round(float(step))), safe_total))
    remaining = max(0, safe_total - safe_step)
    return _tr(
        'PRELOAD_COUNTER_REMAINING',
        current=safe_step,
        total=safe_total,
        remaining=remaining,
    )


def is_preload_target(target: str) -> bool:
    return isinstance(target, str) and target.startswith(_PRELOAD_TARGET_PREFIX)


def extract_preload_widget_rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    extracted: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue

        targets = entry.get('targets')
        if not isinstance(targets, list):
            continue

        matched_targets = [
            text
            for target in targets
            if isinstance(target, str) and (text := target.strip()) and is_preload_target(text)
        ]
        if not matched_targets:
            continue

        copied = deepcopy(entry)
        copied['targets'] = matched_targets
        extracted.append(copied)

    return extracted


def build_preload_theme_payload(theme: dict[str, Any]) -> dict[str, Any]:
    widgets = theme.get('widgets') if isinstance(theme, dict) else None
    return {'widgets': extract_preload_widget_rules(widgets)}


def build_preload_window_theme_payload(theme: dict[str, Any]) -> dict[str, Any]:
    payload = build_preload_theme_payload(theme)
    extracted: list[dict[str, Any]] = []
    for entry in payload.get('widgets', []):
        if not isinstance(entry, dict):
            continue
        targets = [target for target in entry.get('targets', []) if target == _PRELOAD_WINDOW_TARGET]
        if not targets:
            continue
        copied = deepcopy(entry)
        copied['targets'] = targets
        extracted.append(copied)
    return {'widgets': extracted}


def build_preload_surface_theme_payload(theme: dict[str, Any]) -> dict[str, Any]:
    payload = build_preload_theme_payload(theme)
    extracted: list[dict[str, Any]] = []
    for entry in payload.get('widgets', []):
        if not isinstance(entry, dict):
            continue
        targets = [target for target in entry.get('targets', []) if target != _PRELOAD_WINDOW_TARGET]
        if not targets:
            continue
        copied = deepcopy(entry)
        copied['targets'] = targets
        extracted.append(copied)
    return {'widgets': extracted}


def resolve_preload_window_radius_px(theme: dict[str, Any], width: float, height: float) -> float:
    window_styles = resolve_preload_target_styles(theme, _PRELOAD_WINDOW_TARGET)
    border_data = window_styles.get('border') if isinstance(window_styles.get('border'), dict) else {}
    radius_value = str(border_data.get('radius', '')).strip()
    if not radius_value:
        screen_styles = resolve_preload_target_styles(theme, _PRELOAD_SCREEN_TARGET)
        border_data = screen_styles.get('border') if isinstance(screen_styles.get('border'), dict) else {}
        radius_value = str(border_data.get('radius', '')).strip()
    max_radius = max(0.0, min(float(width), float(height)) / 2.0)

    if radius_value.endswith('%'):
        try:
            percent = max(0.0, float(radius_value[:-1].strip()))
        except ValueError:
            return 0.0
        return min(max_radius, (min(float(width), float(height)) * percent) / 100.0)

    normalized = radius_value.removesuffix('px').strip()
    try:
        return min(max_radius, max(0.0, float(normalized)))
    except ValueError:
        return 0.0


def resolve_preload_target_styles(theme: dict[str, Any], target: str) -> dict[str, Any]:
    payload = build_preload_theme_payload(theme)
    merged: dict[str, Any] = {}
    for entry in payload.get('widgets', []):
        if not isinstance(entry, dict):
            continue
        if target not in entry.get('targets', []):
            continue
        styles = entry.get('styles')
        if not isinstance(styles, dict):
            continue
        merged = _deep_merge_dicts(merged, styles)
    return merged


def coerce_qcolor(value: Any, fallback: QColor) -> QColor:
    color = to_qcolor(value)
    if color is not None:
        return color
    return QColor(fallback)


def _deep_merge_dicts(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
