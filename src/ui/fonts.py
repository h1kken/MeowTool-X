from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget


def apply_font_antialiasing(target: QFont | QWidget) -> QFont:
    font = QFont(target.font()) if isinstance(target, QWidget) else QFont(target)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if isinstance(target, QWidget):
        target.setFont(font)
    return font


__all__ = ('apply_font_antialiasing',)
