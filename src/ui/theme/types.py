import typing as t
import collections.abc as cabc

if t.TYPE_CHECKING:
    from src.core.types import DataMap

QSSParser = cabc.Callable[[DataMap], list[str]]
QTHandler = cabc.Callable[..., None]


__all__ = (
    'DataMap',
    'ThemeScalar',
    'DataValue',
    'QSSParser',
    'QTHandler',
)
