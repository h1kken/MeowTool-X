from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout

from .widget import MTWidget


class MTPopupOverlay(MTWidget):
    clickedOutside = Signal()
    
    _OBJECT_NAME = 'Overlay'

    def __init__(
        self,
        parent: MTWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, self._OBJECT_NAME))

        self._popup: MTWidget | None = None
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

    def showPopup(self, popup: MTWidget) -> None:
        self.closePopup()
        self._popup = popup
        popup.setParent(self)
        self._main_layout.addWidget(popup, alignment=Qt.AlignmentFlag.AlignCenter)
        self.show()

    def closePopup(self) -> None:
        if self._popup is None:
            return

        self._main_layout.removeWidget(self._popup)
        self._popup.deleteLater()
        self._popup = None
        self.hide()

    def togglePopup(self, popup: MTWidget) -> None:
        self.showPopup(popup) if self._popup is None else self.closePopup()

    def mousePressEvent(self, event: QMouseEvent):
        self.closePopup()
        super().mousePressEvent(event)
