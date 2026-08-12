from __future__ import annotations

import typing as t

from copy import deepcopy

from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.core.types import DataValue, DataMap


def resolve_theme(theme: DataMap) -> DataMap:
    raw_vars = theme.get('vars')

    if not isinstance(raw_vars, dict):
        return deepcopy(theme)

    resolved_vars = _resolve_vars_map(raw_vars)

    resolved_theme = {
        key: _resolve_theme_value(value, resolved_vars)
            for key, value in theme.items()
                if key != 'vars'
    }

    return resolved_theme


def _resolve_vars_map(vars_map: DataMap) -> DataMap:
    resolved: DataMap = {}

    def resolve_var(name: str, stack: tuple[str, ...]) -> DataValue:
        if name in resolved:
            return resolved[name]

        if name in stack:
            logger.error(f'Circular variable reference: {' > '.join((*stack, name))}')

        value = _resolve_value(vars_map[name], stack + (name,))
        resolved[name] = value
        return value

    def _resolve_value(value: DataValue, stack: tuple[str, ...]) -> DataValue:
        if isinstance(value, str):
            ref = _normalize_var(value)

            if ref is None or ref not in vars_map:
                return value

            return resolve_var(ref, stack)

        if isinstance(value, list):
            return [_resolve_value(item, stack) for item in value]

        if isinstance(value, dict):
            return {
                key: _resolve_value(item, stack)
                for key, item in value.items()
            }

        return value

    for name in vars_map:
        resolve_var(name, ())

    return resolved


def _normalize_var(value: str) -> str | None:
    value = value.strip()

    if value.startswith('var('):
        if not value.endswith(')'):
            return None

        value = value[4:-1].strip()

    if not value.startswith('--'):
        return None

    if any(char.isspace() for char in value):
        return None

    return value


def _resolve_theme_value(value: DataValue, vars_map: DataMap) -> DataValue:
    if isinstance(value, str):
        ref = _normalize_var(value)
        if ref is None or ref not in vars_map:
            return value

        return deepcopy(vars_map[ref])

    if isinstance(value, list):
        return [_resolve_theme_value(item, vars_map) for item in value]

    if isinstance(value, dict):
        return {key: _resolve_theme_value(item, vars_map) for key, item in value.items()}

    return value
