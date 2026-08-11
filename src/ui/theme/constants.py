from PySide6.QtCore import Qt


SIDES = ('top', 'right', 'bottom', 'left')

ALIGNMENT_FLAGS: dict[str, Qt.AlignmentFlag] = {
    'top': Qt.AlignmentFlag.AlignTop,
    'right': Qt.AlignmentFlag.AlignRight,
    'bottom': Qt.AlignmentFlag.AlignBottom,
    'left': Qt.AlignmentFlag.AlignLeft,
    'center': Qt.AlignmentFlag.AlignCenter,
    'hcenter': Qt.AlignmentFlag.AlignHCenter,
    'vcenter': Qt.AlignmentFlag.AlignVCenter,
    'justify': Qt.AlignmentFlag.AlignJustify,
    'baseline': Qt.AlignmentFlag.AlignBaseline,
    'absolute': Qt.AlignmentFlag.AlignAbsolute,
}


__all__ = (
    'SIDES',
    'ALIGNMENT_FLAGS',
)
