from copy import deepcopy
import typing as t

from src.config.types import ConfigMap, ConfigValue
from src.config.constants import CONFIG_COMMENT_SYMBOLS, CONFIG_INDENT
from src.utils.string import safe_literal_eval


def parse_config(text: str) -> ConfigMap:
    parsed: ConfigMap = {}
    stack: list[tuple[ConfigMap, int]] = [(parsed, -1)]

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(CONFIG_COMMENT_SYMBOLS):
            continue

        indent = _count_indent_levels(line)
        line = stripped

        if ':' in line:
            key, value = map(str.strip, line.split(':', 1))
            stack[-1][0][key] = t.cast(ConfigValue, safe_literal_eval(value))
        else:
            while stack and stack[-1][1] >= indent:
                stack.pop()
            new_dict: ConfigMap = {}
            stack[-1][0][line] = new_dict
            stack.append((new_dict, indent))

    return parsed


def normalize_config(
    user_config: ConfigMap,
    default_config: ConfigMap,
    *,
    keep_unknown: bool = True,
    recovery_missing: bool = False,
) -> ConfigMap:
    validated: ConfigMap = {}
    
    for key, default_value in default_config.items():
        if key not in user_config:
            if recovery_missing:
                if isinstance(default_value, dict):
                    validated[key] = normalize_config(
                        {},
                        default_value,
                        keep_unknown=keep_unknown,
                        recovery_missing=recovery_missing,
                    )
                else:
                    validated[key] = _clone_default(default_value)
            continue

        user_value = user_config[key]

        if isinstance(default_value, dict):
            if isinstance(user_value, dict):
                validated[key] = normalize_config(
                    user_value,
                    default_value,
                    keep_unknown=keep_unknown,
                    recovery_missing=recovery_missing,
                )
            else:
                validated[key] = normalize_config(
                    {},
                    default_value,
                    keep_unknown=keep_unknown,
                    recovery_missing=recovery_missing,
                )
        else:
            validated[key] = t.cast(ConfigValue, convert_value(user_value, default_value))

    if keep_unknown:
        for key, user_value in user_config.items():
            if key in default_config:
                continue
            if isinstance(user_value, dict):
                validated[key] = normalize_config(
                    user_value,
                    {},
                    keep_unknown=True,
                    recovery_missing=recovery_missing,
                )
            else:
                validated[key] = t.cast(ConfigValue, convert_value(user_value))

    return validated


def convert_value(user_value: object | None = None, default_value: ConfigValue | None = None) -> ConfigValue | object | None:
    if default_value is not None:
        return _convert_user_value(user_value, default_value)

    if isinstance(user_value, str):
        parsed = _convert_to_bool(user_value)
        if isinstance(parsed, bool):
            return parsed
    return user_value


def _count_indent_levels(raw_line: str) -> int:
    leading = raw_line[: len(raw_line) - len(raw_line.lstrip(' \t'))]
    if not leading:
        return 0

    indent_unit = max(1, len(CONFIG_INDENT))
    tabs = leading.count('\t')
    spaces = leading.count(' ') // indent_unit
    return tabs + spaces


def _clone_default(default_value: ConfigValue) -> ConfigValue:
    if isinstance(default_value, tuple):
        return deepcopy(default_value[0]) if default_value else None
    return t.cast(ConfigValue, deepcopy(default_value))


def _convert_to_bool(user_value: str) -> bool | str:
    low = user_value.strip().lower()
    if low in ('true', 'yes', 'да', 'on', '+'):
        return True
    if low in ('false', 'no', 'нет', 'off', '-'):
        return False
    return user_value


def _parse_numeric(value: object) -> object:
    if isinstance(value, str):
        return safe_literal_eval(value)
    return value


def _is_numeric_bound_tuple(value: tuple[ConfigValue, ...]) -> t.TypeGuard[tuple[int | float, int | float, int | float]]:
    return (len(value) == 3) and all(type(item) in (int, float) for item in value)


def _convert_user_value(user_value: object, default_value: ConfigValue) -> ConfigValue:
    # tuple
    if isinstance(default_value, tuple):
        if _is_numeric_bound_tuple(default_value):
            default_scalar, min_value, max_value = default_value
            parsed = _parse_numeric(user_value)

            if isinstance(default_scalar, int) and not isinstance(default_scalar, bool):
                if (
                    isinstance(parsed, bool)
                    or (isinstance(parsed, float) and not parsed.is_integer())
                    or not isinstance(parsed, (int, float))
                ):
                    return default_scalar
                parsed = int(parsed)
            elif isinstance(default_scalar, float):
                if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
                    return default_scalar
                parsed = float(parsed)
            else:
                return _clone_default(default_value)

            if min_value <= parsed <= max_value:
                return parsed
            return default_scalar

        return _clone_default(default_value)

    # bool
    if isinstance(default_value, bool):
        if isinstance(user_value, str):
            parsed = _convert_to_bool(user_value)
            if isinstance(parsed, bool):
                return parsed
            return default_value
        if isinstance(user_value, bool):
            return user_value
        return default_value

    # int and not bool
    if isinstance(default_value, int) and not isinstance(default_value, bool):
        parsed = _parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, int):
            return parsed
        if isinstance(parsed, float) and parsed.is_integer():
            return int(parsed)
        return default_value

    # float
    if isinstance(default_value, float):
        parsed = _parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, (int, float)):
            return float(parsed)
        return default_value

    # str
    if isinstance(default_value, str):
        if user_value is None:
            return default_value
        return str(user_value)

    # list
    if isinstance(default_value, list):
        if isinstance(user_value, list):
            return t.cast(ConfigValue, deepcopy(t.cast(list[ConfigValue], user_value)))
        return t.cast(ConfigValue, deepcopy(default_value))

    # dict
    if isinstance(default_value, dict):
        if isinstance(user_value, dict):
            return t.cast(ConfigValue, deepcopy(t.cast(ConfigMap, user_value)))
        return t.cast(ConfigValue, deepcopy(default_value))

    if user_value is None:
        return _clone_default(default_value)

    return t.cast(ConfigValue, user_value)
