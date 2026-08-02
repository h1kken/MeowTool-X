from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class MTWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)

    # TODO: return it if problems
    # def paintEvent(self, event: QPaintEvent) -> None:
    #     painter = new_widget_painter(self, antialias=False)
    #     draw_widget_background(self, painter)
    #     painter.end()
    #     super().paintEvent(event)
