from PySide6.QtWidgets import QWidget


def normalize_obj_name(base: str, suffix: str) -> str:
    return f'{base}_{suffix}' if base else ''


def repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
