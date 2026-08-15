from dataclasses import dataclass

from PySide6.QtCore import Qt, QEvent, QModelIndex
from PySide6.QtGui import QHelpEvent, QPainter, QFontMetrics
from PySide6.QtWidgets import QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QToolTip


@dataclass(slots=True)
class PathDelegateStyle:
    elide_mode: Qt.TextElideMode


class PathDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None: # type: ignore[override]
        metrics = QFontMetrics(option.font)

        text = metrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole)),
            Qt.TextElideMode.ElideMiddle,
            option.rect.width(),
        )

        painter.drawText(
            option.rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )

    def helpEvent(self, event: QHelpEvent, view: QAbstractItemView, _option: QStyleOptionViewItem, index: QModelIndex) -> bool: # type: ignore[override]
        if not index.isValid():
            return False
        if event.type() != QEvent.Type.ToolTip:
            return False

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return False

        QToolTip.showText(event.globalPos(), str(text), view)
        return True
