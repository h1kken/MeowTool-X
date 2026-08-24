import collections.abc as cabc

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from src.app.paths import PATH_ICONS_SRC
from src.translation import TranslationKey as TrKey
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.helpers import repolish

from .icon import MTIcon
from .label import MTLabel
from .widget import MTWidget

class _CollapsibleHeader(MTWidget):
    clicked = Signal()
    
    _OBJECT_NAME = 'Header'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, _CollapsibleHeader._OBJECT_NAME))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setExpanded(True)
        
        self._build_ui(tr=tr)
    
    def _build_ui(
        self,
        *,
        tr: TrKey = TrKey(),
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.HBOX, self)
        
        self._label = MTLabel(tr=tr, obj_name=(obj_name, 'Title'))
        self._main_layout.addWidget(self._label)
        
        self._main_layout.addStretch()
        
        self._icon = MTIcon(obj_name=(obj_name,), source=str(PATH_ICONS_SRC / 'arrow-right.svg'))
        self._main_layout.addWidget(self._icon)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def setExpanded(self, expanded: bool):
        self.setProperty('expanded', expanded)
        self._icon.setRotation(90 if expanded else 0)
        repolish(self)


class MTCollapsibleContainer(MTWidget):
    toggled = Signal(bool)
    
    _OBJECT_NAME = 'Container'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
        expanded: bool = True,
        widgets: cabc.Sequence[QWidget] | None = None,
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, MTCollapsibleContainer._OBJECT_NAME))

        self._expanded = expanded
        
        self._build_ui(tr=tr, widgets=widgets)
        self._connect_signals()
        
    def _build_ui(
        self,
        *,
        tr: TrKey,
        widgets: cabc.Sequence[QWidget] | None
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._header = _CollapsibleHeader(self, tr=tr, obj_name=(obj_name,))
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._main_layout.addWidget(self._header)
        
        self._separator = MTWidget(obj_name=(obj_name, 'Separator'))
        self._separator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._separator.setFixedHeight(1)
        self._main_layout.addWidget(self._separator)

        self._content_widget = MTWidget(obj_name=(obj_name, 'Content'))
        self._content_layout = create_layout(LayoutType.VBOX, self._content_widget)
        self._main_layout.addWidget(self._content_widget)

        for widget in widgets or []:
            self._content_layout.addWidget(widget)

    def _connect_signals(self) -> None:
        self._header.clicked.connect(self.toggle)

    def isExpanded(self) -> bool:
        return self._expanded

    def setExpanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return

        self._expanded = expanded
        
        self._header.setExpanded(expanded)

        self.setProperty('expanded', expanded)
        
        self._separator.setVisible(expanded)
        self._content_widget.setVisible(expanded)

        repolish(self)

        self.toggled.emit(expanded)

    def toggle(self) -> None:
        self.setExpanded(not self._expanded)

    def addWidget(self, widget: MTWidget) -> None:
        self._content_layout.addWidget(widget)
    
    def removeWidget(self, widget: MTWidget) -> None:
        self._content_layout.removeWidget(widget)
