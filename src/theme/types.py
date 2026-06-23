from typing import TypedDict

from PySide6.QtWidgets import QWidget

from src.theme.schema.types import ThemeMap

type ThemeWidgetsMap = dict[str, ThemeMap]
type RuntimeStylesMap = dict[QWidget, ThemeMap]
type GeometrySnapshot = dict[str, int]


class LayoutSnapshot(TypedDict):
    margin: tuple[int, int, int, int]
    spacing: int
    alignment: int
    justify_indices: list[int]


type ThemeChangePayload = tuple[ThemeMap, ThemeWidgetsMap]

__all__ = (
    "GeometrySnapshot",
    "LayoutSnapshot",
    "RuntimeStylesMap",
    "ThemeChangePayload",
    "ThemeWidgetsMap",
)
