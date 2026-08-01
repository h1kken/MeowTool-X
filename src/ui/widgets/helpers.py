from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def normalize_obj_name(base: str, suffix: str) -> str:
    return f'{base}_{suffix}' if base else ''


def repolish(widget: QWidget) -> None:
    if not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
        widget.update()
        return

    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
