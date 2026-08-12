from copy import deepcopy
import typing as t

from src.config.constants import CONFIG_COMMENT_SYMBOLS, CONFIG_INDENT
from src.utils.mappings import clone_value, merge_dicts
from src.utils.string import safe_literal_eval

if t.TYPE_CHECKING:
    from src.core.types import DataValue, DataMap


def normalize_config(
    user_config: DataMap,
    default_config: DataMap,
    *,
    keep_unknown: bool = True,
    recovery_missing: bool = False,
) -> DataMap:
    return merge_dicts(
        user_config,
        default_config,
        converter=convert_value,
        keep_unknown=keep_unknown,
        recovery_missing=recovery_missing,
    )


def parse_config(text: str) -> DataMap:
    parsed: DataMap = {}
    stack: list[tuple[DataMap, int]] = [(parsed, -1)]

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(CONFIG_COMMENT_SYMBOLS):
            continue

        indent = _count_indent_levels(line)
        line = stripped

        if ':' in line:
            key, value = map(str.strip, line.split(':', 1))
            stack[-1][0][key] = t.cast(DataValue, safe_literal_eval(value))
        else:
            while stack and stack[-1][1] >= indent:
                stack.pop()
            new_dict: DataMap = {}
            stack[-1][0][line] = new_dict
            stack.append((new_dict, indent))

    return parsed


def convert_value(user_value: object | None = None, default_value: DataValue | None = None) -> DataValue | object | None:
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


def _is_numeric_bound_tuple(value: tuple[DataValue, ...]) -> t.TypeGuard[tuple[int | float, int | float, int | float]]:
    return (len(value) == 3) and all(type(item) in (int, float) for item in value)


def _convert_user_value(user_value: object, default_value: DataValue) -> DataValue:
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
                return clone_value(default_value)

            if min_value <= parsed <= max_value:
                return parsed
            return default_scalar

        return clone_value(default_value)

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
            return t.cast(DataValue, deepcopy(t.cast(list[DataValue], user_value)))
        return t.cast(DataValue, deepcopy(default_value))

    # dict
    if isinstance(default_value, dict):
        if isinstance(user_value, dict):
            return t.cast(DataValue, deepcopy(t.cast(DataMap, user_value)))
        return t.cast(DataValue, deepcopy(default_value))

    if user_value is None:
        return clone_value(default_value)

    return t.cast(DataValue, user_value)
