import typing as t

from src.utils.mappings import merge_dicts

if t.TYPE_CHECKING:
    from src.core.types import DataMap


def normalize_theme(
    user_map: DataMap,
    default_map: DataMap,
    *,
    keep_unknown: bool = True,
    recovery_missing: bool = False,
) -> DataMap:
    return merge_dicts(
        user_map,
        default_map,
        keep_unknown=keep_unknown,
        recovery_missing=recovery_missing,
    )
