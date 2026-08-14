import typing as t

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget

from src.ui.layouts.enums import LayoutType
from src.utils.qt import build_object_name


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
            layout = QHBoxLayout()
        case LayoutType.VBOX:
            layout = QVBoxLayout()
        case LayoutType.GRID:
            layout = QGridLayout()

    if parent is not None:
        parent.setLayout(layout)
        layout.setObjectName(build_object_name((parent.objectName(), 'Layout')))
        
    layout.setContentsMargins(*(margins, margins, margins, margins) if isinstance(margins, int) else margins)
    layout.setSpacing(spacing)

    return layout
