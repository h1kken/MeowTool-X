from dataclasses import dataclass, field
from uuid import UUID

from PySide6.QtCore import Qt, QObject, QSize, QRect, QEvent, QModelIndex, Signal
from PySide6.QtGui import QColor, QPixmap, QPen, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from src.app.paths import PATH_ICONS_SRC
from src.ui.icons import build_icon_pixmap

from ..model import PrepareTableModel


@dataclass(slots=True)
class DelegateButtonStyle:    
    background: QColor = field(default_factory=QColor)
    
    border_style: Qt.PenStyle = Qt.PenStyle.NoPen
    border_color: QColor = field(default_factory=QColor)
    border_width: int = 0
    border_radius: int = 0
    
    button_size: QSize = field(default_factory=lambda: QSize(20, 20))
    
    icon: QPixmap = field(default_factory=lambda: build_icon_pixmap(source=str(PATH_ICONS_SRC / 'actions' / 'close.svg'))) # delete*
    icon_size: int = 16


@dataclass(slots=True)
class DelegateButtonStateStyle:
    normal  : DelegateButtonStyle = field(default_factory=DelegateButtonStyle)
    hover   : DelegateButtonStyle | None = None
    pressed : DelegateButtonStyle | None = None


class DeleteButtonDelegate(QStyledItemDelegate):
    clicked = Signal(UUID)

    _COLUMN = 2

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        
        self._style = DelegateButtonStateStyle()

    def setStyle(self, style: DelegateButtonStateStyle) -> None:
        self._style = style

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None: # type: ignore[override]
        super().paint(painter, option, index)
        
        style = self._style.normal
        if option.state & QStyle.StateFlag.State_Sunken:
            style = self._style.pressed or style
        elif option.state & QStyle.StateFlag.State_MouseOver:
            style = self._style.hover or style

        rect = option.rect
        
        button_size = QSize(
            min(style.button_size.width(), rect.width()),
            min(style.button_size.height(), rect.height()),
        )
        button_rect = QRect(0, 0, button_size.width(), button_size.height())
        button_rect.moveCenter(rect.center())

        painter.setPen(QPen(style.border_color, style.border_width))
        painter.setBrush(style.background)

        painter.drawRoundedRect(button_rect, style.border_radius, style.border_radius)

        if not style.icon.isNull():
            icon_rect = style.icon.rect()
            icon_rect.moveCenter(rect.center())
            painter.drawPixmap(icon_rect, style.icon)

    def editorEvent(self, event: QEvent, model: PrepareTableModel, _option: QStyleOptionViewItem, index: QModelIndex) -> bool: # type: ignore[override]
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if index.column() != self._COLUMN:
            return False

        item = model.item_at(index.row())
        if item is None:
            return False

        self.clicked.emit(item.id)
        return True
