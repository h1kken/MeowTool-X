import typing as t
import collections.abc as cabc

from copy import deepcopy

if t.TYPE_CHECKING:
    from src.core.types import DataValue, DataMap


def merge_dicts(
    user_config: DataMap,
    default_config: DataMap,
    *,
    converter: cabc.Callable[[object | None, DataValue | None], t.Any] | None = None,
    keep_unknown: bool = True,
    recovery_missing: bool = False,
) -> DataMap:
    validated: DataMap = {}
    
    for key, default_value in default_config.items():
        if key not in user_config:
            if recovery_missing:
                if isinstance(default_value, dict):
                    validated[key] = merge_dicts(
                        {},
                        default_value,
                        converter=converter,
                        keep_unknown=keep_unknown,
                        recovery_missing=recovery_missing,
                    )
                else:
                    validated[key] = clone_value(default_value)
            continue

        user_value = user_config[key]

        if not isinstance(default_value, dict):
            validated[key] = t.cast(DataValue, converter(user_value, default_value)) if converter else user_value
            continue
            
        validated[key] = merge_dicts(
            user_value if isinstance(user_value, dict) else {},
            default_value,
            converter=converter,
            keep_unknown=keep_unknown,
            recovery_missing=recovery_missing,
        )

    if keep_unknown:
        for key, user_value in user_config.items():
            if key in default_config:
                continue
            
            if isinstance(user_value, dict):
                validated[key] = merge_dicts(
                    user_value,
                    {},
                    converter=converter,
                    recovery_missing=recovery_missing,
                )
            else:
                validated[key] = t.cast(DataValue, converter(user_value, None)) if converter else user_value

    return validated


def clone_value(value: DataValue) -> DataValue:
    if isinstance(value, tuple):
        return deepcopy(value[0]) if value else None
    return deepcopy(value)
