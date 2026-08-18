from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy


SIDES = ('top', 'right', 'bottom', 'left')

DEFAULT_CONTENT_MARGINS = (0, 0, 0, 0)
DEFAULT_SPACING = 0

DEFAULT_ALIGNMENT = Qt.AlignmentFlag(0)
ALIGNMENT_FLAGS: dict[str, Qt.AlignmentFlag] = {
    'top'      : Qt.AlignmentFlag.AlignTop,
    'right'    : Qt.AlignmentFlag.AlignRight,
    'bottom'   : Qt.AlignmentFlag.AlignBottom,
    'left'     : Qt.AlignmentFlag.AlignLeft,
    'center'   : Qt.AlignmentFlag.AlignCenter,
    'hcenter'  : Qt.AlignmentFlag.AlignHCenter,
    'vcenter'  : Qt.AlignmentFlag.AlignVCenter,
    'justify'  : Qt.AlignmentFlag.AlignJustify,
    'baseline' : Qt.AlignmentFlag.AlignBaseline,
    'absolute' : Qt.AlignmentFlag.AlignAbsolute,
}

DEFAULT_SIZE_POLICIES = (QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
SIZE_POLICIES: dict[str, QSizePolicy.Policy] = {
    'fixed'             : QSizePolicy.Policy.Fixed,
    'minimum'           : QSizePolicy.Policy.Minimum,
    'minimum_expanding' : QSizePolicy.Policy.MinimumExpanding,
    'maximum'           : QSizePolicy.Policy.Maximum,
    'preferred'         : QSizePolicy.Policy.Preferred,
    'expanding'         : QSizePolicy.Policy.Expanding,
    'ignored'           : QSizePolicy.Policy.Ignored,
}


__all__ = [name for name in globals()]
