from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QScrollArea

from src.utils.qt import build_object_name


class MTScrollArea(QScrollArea):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            parent,
            widgetResizable=True,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(20)
        self.setObjectName(build_object_name(obj_name))
