from typing import Literal, overload

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget

from src.ui.layouts.enums import LayoutType


@overload
def create_layout(layout_type: Literal[LayoutType.HBOX], *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0, parent: QWidget | None = None) -> QHBoxLayout: ...
@overload
def create_layout(layout_type: Literal[LayoutType.VBOX], *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0, parent: QWidget | None = None) -> QVBoxLayout: ...
@overload
def create_layout(layout_type: Literal[LayoutType.GRID], *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0, parent: QWidget | None = None) -> QGridLayout: ...

def create_layout(
    layout_type: LayoutType,
    *,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = 0,
    parent: QWidget | None = None,
) -> QLayout:
    match layout_type:
        case LayoutType.HBOX:
            layout = QHBoxLayout(parent) if parent is not None else QHBoxLayout()
        case LayoutType.VBOX:
            layout = QVBoxLayout(parent) if parent is not None else QVBoxLayout()
        case LayoutType.GRID:
            layout = QGridLayout(parent) if parent is not None else QGridLayout()
        case _:
            raise ValueError(f'Unknown layout type: {layout_type}')

    layout.setContentsMargins(*(margins, margins, margins, margins) if isinstance(margins, int) else margins)
    layout.setSpacing(spacing)

    return layout
