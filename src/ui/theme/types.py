import typing as t
import collections.abc as cabc


type ThemeScalar = None | bool | int | float | str
type ThemeValue = (
    ThemeScalar
    | list['ThemeValue']
    | tuple['ThemeValue', ...]
    | dict[str, 'ThemeValue']
)
ThemeMap: t.TypeAlias = dict[str, ThemeValue]

QSSParser = cabc.Callable[[ThemeMap], list[str]]
QTHandler = cabc.Callable[..., None]


__all__ = (
    'ThemeMap',
    'ThemeScalar',
    'ThemeValue',
    'QSSParser',
    'QTHandler',
)
