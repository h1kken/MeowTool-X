import typing as t

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget

from src.ui.layouts.enums import LayoutType


@t.overload
def create_layout(layout_type: t.Literal[LayoutType.HBOX], parent: QWidget | None = None, *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0) -> QHBoxLayout: ...
@t.overload
def create_layout(layout_type: t.Literal[LayoutType.VBOX], parent: QWidget | None = None, *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0) -> QVBoxLayout: ...
@t.overload
def create_layout(layout_type: t.Literal[LayoutType.GRID], parent: QWidget | None = None, *, margins: int | tuple[int, int, int, int] = 0, spacing: int = 0) -> QGridLayout: ...

def create_layout(
    layout_type: LayoutType,
    parent: QWidget | None = None,
    *,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = 0,
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

    if parent:
        layout.setObjectName(f'{parent.objectName()}_Layout')
        
    layout.setContentsMargins(*(margins, margins, margins, margins) if isinstance(margins, int) else margins)
    layout.setSpacing(spacing)

    return layout
