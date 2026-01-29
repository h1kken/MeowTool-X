from typing import Literal, Optional, overload
from src.ui.layouts.enums import LayoutType
from PySide6.QtWidgets import (
    QLayout, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout
)


@overload
def create_layout(layout_type: Literal[LayoutType.HBOX], *, margins: tuple[int, int, int, int] = (0, 0, 0, 0), spacing: int = 0, parent: Optional[QWidget] = None) -> QHBoxLayout: ...
@overload
def create_layout(layout_type: Literal[LayoutType.VBOX], *, margins: tuple[int, int, int, int] = (0, 0, 0, 0), spacing: int = 0, parent: Optional[QWidget] = None) -> QVBoxLayout: ...
@overload
def create_layout(layout_type: Literal[LayoutType.GRID], *, margins: tuple[int, int, int, int] = (0, 0, 0, 0), spacing: int = 0, parent: Optional[QWidget] = None) -> QGridLayout: ...

def create_layout(
    layout_type: LayoutType,
    *,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    spacing: int = 0,
    parent: Optional[QWidget] = None,
) -> QLayout:
    match layout_type:
        case LayoutType.HBOX: layout = QHBoxLayout(parent)
        case LayoutType.VBOX: layout = QVBoxLayout(parent)
        case LayoutType.GRID: layout = QGridLayout(parent)
        case _:
            raise ValueError(f'Unknown layout type: {layout_type}')

    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)

    return layout