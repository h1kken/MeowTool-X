from __future__ import annotations

import typing as t

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QHideEvent, QMouseEvent, QRegion, QResizeEvent, QShowEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QBoxLayout, QLayout, QSizePolicy, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTWidget
from src.ui.widgets.paint_primitives import resolve_uniform_radius, rounded_rect_path
from src.ui.widgets.types import PopupPlacement


class _PopupBackdrop(MTWidget):
    def __init__(
        self,
        parent: QWidget,
        *,
        popup: MTPopup,
    ) -> None:
        super().__init__(parent, obj_name=f'{popup.objectName()}_Backdrop_Widget')
        self._popup = popup
        self.setProperty('popupBackdrop', True)
        self.setProperty('popup', True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._popup.close_on_outside_click:
            self._popup.hide()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None: event.accept()
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None: event.accept()
    def wheelEvent(self, event: QWheelEvent) -> None: event.accept()


class MTPopup(MTWidget):
    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
        layout_type: LayoutType = LayoutType.VBOX,
        close_on_outside_click: bool = True,
    ) -> None:
        super().__init__(parent, obj_name=obj_name)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.Tool
        )
        self._close_on_outside_click = bool(close_on_outside_click)
        self._backdrop: _PopupBackdrop | None = None
        self._backdrop_parent: QWidget | None = None
        self._modal_host: QWidget | None = None
        self._last_show_mode: str | None = None
        self._last_offset = QPoint(0, 0)
        self.setProperty('popup', True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self._root_layout = create_layout(LayoutType.VBOX, self)
        self._content = MTWidget(parent=self, obj_name=f'{obj_name}_Content')
        self._content.setProperty('popupContent', True)
        self._content_layout = create_layout(layout_type, parent=self._content)
        self._root_layout.addWidget(self._content)

    @property
    def close_on_outside_click(self) -> bool: return self._close_on_outside_click

    @property
    def content_widget(self) -> MTWidget: return self._content

    @property
    def content_layout(self) -> QLayout: return self._content_layout

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        if isinstance(self._content_layout, QBoxLayout):
            self._content_layout.addWidget(widget, stretch)
            return

        grid_layout = self._content_layout
        row = grid_layout.rowCount()
        grid_layout.addWidget(widget, row, 0)

    def clear(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _sync_shape_mask(self) -> None:
        self._apply_shape_mask()

    def show_for(
        self,
        anchor: QWidget,
        *,
        placement: PopupPlacement = 'bottom-left',
        offset: QPoint | tuple[int, int] = QPoint(0, 0),
        match_width: bool = False,
    ) -> None:
        self._last_show_mode = 'anchored'
        self._last_offset = self._normalize_offset(offset)
        if match_width:
            self.setFixedWidth(max(1, anchor.width()))
        self._prepare_to_show()

        popup_rect = QRect(QPoint(0, 0), self.sizeHint().expandedTo(self.minimumSizeHint()))
        popup_rect.moveTopLeft(self._placement_point(anchor, popup_rect.size(), placement))
        popup_rect.translate(self._last_offset)
        popup_rect.moveTopLeft(self._clamped_top_left(popup_rect))
        self.move(popup_rect.topLeft())
        self.show()
        self.raise_()
        self.opened.emit()

    def show_centered(self, parent: QWidget | None = None, *, offset: QPoint | tuple[int, int] = QPoint(0, 0)) -> None:
        embedded_parent = self.parentWidget() if isinstance(self.parentWidget(), QWidget) else None
        if embedded_parent is not None:
            parent = embedded_parent
        else:
            parent = parent or QApplication.activeWindow()
        self._last_show_mode = 'centered'
        self._last_offset = self._normalize_offset(offset)
        self._prepare_to_show()
        self._move_centered(parent)
        self.show()
        self.raise_()
        self.opened.emit()

    def show_at_cursor(self, *, offset: QPoint | tuple[int, int] = QPoint(0, 0)) -> None:
        self._last_show_mode = 'cursor'
        self._last_offset = self._normalize_offset(offset)
        self._prepare_to_show()
        popup_rect = QRect(QPoint(0, 0), self.sizeHint().expandedTo(self.minimumSizeHint()))
        parent_widget = self.parentWidget()
        if isinstance(parent_widget, QWidget):
            local_cursor = parent_widget.mapFromGlobal(QCursor.pos())
            popup_rect.moveTopLeft(local_cursor + self._last_offset)
        else:
            popup_rect.moveTopLeft(QCursor.pos() + self._last_offset)
        popup_rect.moveTopLeft(self._clamped_top_left(popup_rect))
        self.move(popup_rect.topLeft())
        self.show()
        self.raise_()
        self.opened.emit()

    def toggle_for(
        self,
        anchor: QWidget,
        *,
        placement: PopupPlacement = 'bottom-left',
        offset: QPoint | tuple[int, int] = QPoint(0, 0),
        match_width: bool = False,
    ) -> None:
        if self.isVisible():
            self.hide()
            return
        self.show_for(anchor, placement=placement, offset=offset, match_width=match_width)

    def set_modal_host(self, host: QWidget | None) -> None:
        self._modal_host = host
        if isinstance(host, QWidget):
            self.setParent(host, Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        if self._backdrop_parent is not None and self._backdrop_parent is not host:
            self._backdrop_parent.removeEventFilter(self)
            self._backdrop_parent = None
        if self._backdrop is not None and (host is None or self._backdrop.parentWidget() is not host):
            self._backdrop.deleteLater()
            self._backdrop = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_shape_mask()

    def showEvent(self, event: QShowEvent) -> None:
        self.activateWindow()
        self.raise_()
        super().showEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        self._hide_backdrop()
        self.closed.emit()
        super().hideEvent(event)

    def _prepare_to_show(self) -> None:
        self.ensurePolished()
        self.adjustSize()
        self._content.adjustSize()
        self._ensure_backdrop()
        self._sync_shape_mask()
        self._show_backdrop()

    def _placement_point(self, anchor: QWidget, popup_size: QSize, placement: PopupPlacement) -> QPoint:
        parent_widget = self.parentWidget()
        if isinstance(parent_widget, QWidget):
            anchor_top_left = anchor.mapTo(parent_widget, QPoint(0, 0))
            anchor_rect = QRect(anchor_top_left, anchor.size())
        else:
            anchor_rect = QRect(anchor.mapToGlobal(QPoint(0, 0)), anchor.size())
        match str(placement or 'bottom-left').strip().lower().replace('_', '-'):
            case 'bottom-right':
                return QPoint(anchor_rect.right() - popup_size.width() + 1, anchor_rect.bottom() + 1)
            case 'top-left':
                return QPoint(anchor_rect.left(), anchor_rect.top() - popup_size.height())
            case 'top-right':
                return QPoint(anchor_rect.right() - popup_size.width() + 1, anchor_rect.top() - popup_size.height())
            case 'left-top':
                return QPoint(anchor_rect.left() - popup_size.width(), anchor_rect.top())
            case 'left-bottom':
                return QPoint(anchor_rect.left() - popup_size.width(), anchor_rect.bottom() - popup_size.height() + 1)
            case 'right-top':
                return QPoint(anchor_rect.right() + 1, anchor_rect.top())
            case 'right-bottom':
                return QPoint(anchor_rect.right() + 1, anchor_rect.bottom() - popup_size.height() + 1)
            case 'center':
                rect = QRect(QPoint(0, 0), popup_size)
                rect.moveCenter(anchor_rect.center())
                return rect.topLeft()
            case 'cursor':
                return QCursor.pos()
            case _:
                return QPoint(anchor_rect.left(), anchor_rect.bottom() + 1)

    def _clamped_top_left(self, popup_rect: QRect) -> QPoint:
        if isinstance(self.parentWidget(), QWidget):
            parent_widget = self.parentWidget()
            if not isinstance(parent_widget, QWidget):
                return popup_rect.topLeft()
            bounds = QRect(QPoint(0, 0), parent_widget.size())
            x = min(max(popup_rect.left(), bounds.left()), max(bounds.left(), bounds.right() - popup_rect.width() + 1))
            y = min(max(popup_rect.top(), bounds.top()), max(bounds.top(), bounds.bottom() - popup_rect.height() + 1))
            return QPoint(x, y)

        screen = QApplication.screenAt(popup_rect.center()) or QApplication.primaryScreen()
        available = screen.availableGeometry()
        x = min(max(popup_rect.left(), available.left()), max(available.left(), available.right() - popup_rect.width() + 1))
        y = min(max(popup_rect.top(), available.top()), max(available.top(), available.bottom() - popup_rect.height() + 1))
        return QPoint(x, y)

    def _normalize_offset(self, offset: QPoint | tuple[int, int]) -> QPoint:
        if isinstance(offset, QPoint):
            return QPoint(offset)
        if len(offset) >= 2:
            return QPoint(int(offset[0]), int(offset[1]))
        return QPoint(0, 0)

    def _apply_shape_mask(self) -> None:
        radius = resolve_uniform_radius(QRectF(self.rect()), self.property('_themeBorderRadius'))
        if radius <= 0.0:
            self.clearMask()
            return

        rect = QRectF(self.rect())
        path = rounded_rect_path(rect, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._backdrop_parent and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.WindowStateChange,
            QEvent.Type.ZOrderChange,
        }:
            self._sync_backdrop_geometry()
            if self.isVisible():
                self._reposition_visible_popup()
            if self._backdrop is not None and self._backdrop.isVisible():
                self._backdrop.raise_()
            if self.isVisible():
                self.raise_()
        elif watched is self._backdrop_parent and event.type() == QEvent.Type.Hide:
            self.hide()
        return super().eventFilter(watched, event)

    def _resolve_modal_parent(self) -> QWidget | None:
        if isinstance(self._modal_host, QWidget):
            return self._modal_host
        parent_widget = self.parentWidget()
        if isinstance(parent_widget, QWidget):
            parent_window = parent_widget.window()
            host = t.cast(t.Any, parent_window)._popup_modal_host
            if isinstance(host, QWidget):
                return host
            return parent_window
        return QApplication.activeWindow()

    def _ensure_backdrop(self) -> None:
        parent = self._resolve_modal_parent()
        if parent is None:
            return

        if self._backdrop_parent is not parent:
            if self._backdrop_parent is not None:
                self._backdrop_parent.removeEventFilter(self)
            if self._backdrop is not None:
                self._backdrop.deleteLater()
                self._backdrop = None
            self._backdrop_parent = parent
            self._backdrop_parent.installEventFilter(self)

        if self._backdrop is None and self._backdrop_parent is not None:
            self._backdrop = _PopupBackdrop(self._backdrop_parent, popup=self)
            self._backdrop.setGeometry(self._backdrop_parent.rect())

    def _sync_backdrop_geometry(self) -> None:
        if self._backdrop is None or self._backdrop_parent is None:
            return
        self._backdrop.setGeometry(self._backdrop_parent.rect())

    def _show_backdrop(self) -> None:
        self._ensure_backdrop()
        if self._backdrop is None:
            return
        self._sync_backdrop_geometry()
        self._backdrop.show()
        self._backdrop.raise_()
        if self.isVisible():
            self.raise_()

    def _hide_backdrop(self) -> None:
        if self._backdrop is not None:
            self._backdrop.hide()

    def _move_centered(self, parent: QWidget | None = None) -> None:
        popup_size = self.sizeHint().expandedTo(self.minimumSizeHint())
        if isinstance(parent, QWidget) and self.parentWidget() is parent:
            parent_rect = QRect(QPoint(0, 0), parent.size())
        elif isinstance(parent, QWidget):
            parent_rect = QRect(parent.mapToGlobal(QPoint(0, 0)), parent.size())
        else:
            screen = QApplication.primaryScreen()
            parent_rect = screen.availableGeometry()

        popup_rect = QRect(QPoint(0, 0), popup_size)
        popup_rect.moveCenter(parent_rect.center())
        popup_rect.translate(self._last_offset)
        popup_rect.moveTopLeft(self._clamped_top_left(popup_rect))
        self.move(popup_rect.topLeft())

    def _reposition_visible_popup(self) -> None:
        if self._last_show_mode != 'centered':
            return
        embedded_parent = self.parentWidget() if isinstance(self.parentWidget(), QWidget) else None
        self._move_centered(embedded_parent or self._backdrop_parent)
