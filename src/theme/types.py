from src.theme.schema.types import ThemeMap

type ThemeWidgetsMap = dict[str, ThemeMap]
type ThemeChangePayload = tuple[ThemeMap, ThemeWidgetsMap]

__all__ = (
    "ThemeChangePayload",
    "ThemeWidgetsMap",
)
