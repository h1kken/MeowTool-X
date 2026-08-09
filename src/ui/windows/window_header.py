from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QApplication, QWidget

from src.app.paths import PATH_HEADER_ICONS_SRC
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTPlainLabel, MTWidget


_QT_MAX_SIZE = 16_777_215


class MTWindowHeader(MTWidget):
    _OBJECT_NAME = 'Header'
    
    def __init__(self, window: QWidget) -> None:
        super().__init__(parent=window, obj_name=(window.objectName(), self._OBJECT_NAME))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._window = window
        
        self._resize_margin = 4
        self._drag_press_pos = QPoint()
        self._maximized_drag_pending = False
        self._manual_move_active = False
        self._manual_move_offset = QPoint()
        self._manual_resize_active = False
        self._manual_resize_edges: Qt.Edge | None = None
        self._manual_resize_start_global = QPoint()
        self._manual_resize_start_geometry = QRect()
        self._buttons: MTWidget | None = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._title_label = MTPlainLabel(self, text=self._window.windowTitle(), obj_name=(obj_name, 'Title'))
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._main_layout.addStretch()

        self._buttons = MTWidget(self, obj_name=(obj_name, 'Buttons'))
        self._buttons_layout = create_layout(LayoutType.HBOX, self._buttons)
        self._main_layout.addWidget(self._buttons)

        icon_size = QSize(18, 18)

        self._minimize_button = MTButton(obj_name=(obj_name, 'Minimize'))
        self._minimize_button.set_icon(source=str(PATH_HEADER_ICONS_SRC / 'minimize.svg'), size=icon_size)
        self._buttons_layout.addWidget(self._minimize_button)

        self._maximize_button = MTButton(obj_name=(obj_name, 'Maximize'))
        self._maximize_button.set_icon(source=str(PATH_HEADER_ICONS_SRC / 'maximize.svg'), size=icon_size)
        self._buttons_layout.addWidget(self._maximize_button)

        self._close_button = MTButton(obj_name=(obj_name, 'Close'))
        self._close_button.set_icon(source=str(PATH_HEADER_ICONS_SRC / 'close.svg'), size=icon_size)
        self._buttons_layout.addWidget(self._close_button)

        self._window.installEventFilter(self)
        self.sync_window_meta()

    def _connect_signals(self) -> None:
        self._minimize_button.clicked.connect(self._window.showMinimized)
        self._maximize_button.clicked.connect(self._toggle_maximized)
        self._close_button.clicked.connect(self._window.close)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._window:
            match event.type():
                case QEvent.Type.WindowTitleChange | QEvent.Type.WindowStateChange:
                    self.sync_window_meta()
                    self._manual_move_active = False
                    self._maximized_drag_pending = False
                    self.finish_resize()
                case QEvent.Type.Close:
                    self.finish_resize()
                case _:
                    pass
        return super().eventFilter(obj, event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._buttons is not None:
            self._buttons.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() != Qt.MouseButton.LeftButton
            or not self._should_handle_header_drag(event.position().toPoint())
        ):
            super().mousePressEvent(event)
            return

        self._drag_press_pos = event.position().toPoint()
        self._manual_move_active = False
        self._maximized_drag_pending = self._window.isMaximized()

        if not self._maximized_drag_pending:
            if not self._start_system_move():
                self._begin_manual_move(event.globalPosition().toPoint())
            event.accept()
            return

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._manual_move_active and (event.buttons() & Qt.MouseButton.LeftButton):
            self._update_manual_move(event.globalPosition().toPoint())
            event.accept()
            return

        if self._maximized_drag_pending and (
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            moved = event.position().toPoint() - self._drag_press_pos
            if moved.manhattanLength() >= QApplication.startDragDistance():
                self._restore_from_maximized_drag(event.globalPosition().toPoint())
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._manual_move_active = False
            self._maximized_drag_pending = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._should_handle_header_drag(event.position().toPoint())
        ):
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def sync_window_meta(self) -> None:
        self._title_label.setText(self._window.windowTitle())
        self._maximize_button.set_icon(source=str(PATH_HEADER_ICONS_SRC / f'{'restore' if self._window.isMaximized() else 'maximize'}.svg'), size=QSize(18, 18))

    def begin_resize(self, edges: Qt.Edge, global_pos: QPoint) -> None:
        if self._window.isMaximized() or self._window.isFullScreen():
            return
        if self._start_system_resize(edges):
            return
        self._manual_resize_active = True
        self._manual_resize_edges = edges
        self._manual_resize_start_global = QPoint(global_pos)
        self._manual_resize_start_geometry = QRect(self._window.geometry())

    def update_resize(self, global_pos: QPoint) -> None:
        if not self._manual_resize_active or self._manual_resize_edges is None:
            return

        start = self._manual_resize_start_geometry
        dx = global_pos.x() - self._manual_resize_start_global.x()
        dy = global_pos.y() - self._manual_resize_start_global.y()

        x = start.x()
        y = start.y()
        width = start.width()
        height = start.height()

        min_width = max(1, self._window.minimumWidth())
        min_height = max(1, self._window.minimumHeight())
        max_width = self._window.maximumWidth()
        max_height = self._window.maximumHeight()

        if self._manual_resize_edges & Qt.Edge.LeftEdge:
            x += dx
            width -= dx
        elif self._manual_resize_edges & Qt.Edge.RightEdge:
            width += dx

        if self._manual_resize_edges & Qt.Edge.TopEdge:
            y += dy
            height -= dy
        elif self._manual_resize_edges & Qt.Edge.BottomEdge:
            height += dy

        if width < min_width:
            if self._manual_resize_edges & Qt.Edge.LeftEdge:
                x = start.right() - min_width + 1
            width = min_width
        elif 0 < max_width < _QT_MAX_SIZE and width > max_width:
            if self._manual_resize_edges & Qt.Edge.LeftEdge:
                x = start.right() - max_width + 1
            width = max_width

        if height < min_height:
            if self._manual_resize_edges & Qt.Edge.TopEdge:
                y = start.bottom() - min_height + 1
            height = min_height
        elif 0 < max_height < _QT_MAX_SIZE and height > max_height:
            if self._manual_resize_edges & Qt.Edge.TopEdge:
                y = start.bottom() - max_height + 1
            height = max_height

        self._window.setGeometry(x, y, width, height)

    def finish_resize(self) -> None:
        self._manual_resize_active = False
        self._manual_resize_edges = None

    def _toggle_maximized(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_window_meta()

    def _restore_from_maximized_drag(self, global_pos: QPoint) -> None:
        old_width = max(1, self._window.width())
        press_ratio = max(0.0, min(1.0, self._drag_press_pos.x() / old_width))

        normal_geometry = self._window.normalGeometry()
        restored_width = max(1, normal_geometry.width() or self._window.width())
        restored_height = max(1, normal_geometry.height() or self._window.height())
        target_x = global_pos.x() - int(round(restored_width * press_ratio))
        target_y = global_pos.y() - min(self._drag_press_pos.y(), max(0, restored_height - 1))

        screen = QApplication.screenAt(global_pos)
        if screen is not None:
            available = screen.availableGeometry()
            max_x = max(available.left(), available.right() - restored_width + 1)
            max_y = max(available.top(), available.bottom() - restored_height + 1)
            target_x = max(available.left(), min(target_x, max_x))
            target_y = max(available.top(), min(target_y, max_y))

        self._window.showNormal()
        self.sync_window_meta()
        self._window.move(target_x, target_y)

        self._maximized_drag_pending = False
        if not self._start_system_move():
            self._begin_manual_move(global_pos)

    def _begin_manual_move(self, global_pos: QPoint) -> None:
        frame_top_left = self._window.frameGeometry().topLeft()
        self._manual_move_offset = global_pos - frame_top_left
        self._manual_move_active = True

    def _update_manual_move(self, global_pos: QPoint) -> None:
        target = global_pos - self._manual_move_offset
        self._window.move(target)

    def _start_system_move(self) -> bool:
        if self._window.isFullScreen():
            return False
        try:
            return bool(self._window.windowHandle().startSystemMove())
        except RuntimeError:
            return False

    def _start_system_resize(self, edges: Qt.Edge) -> bool:
        try:
            return bool(self._window.windowHandle().startSystemResize(edges))
        except RuntimeError:
            return False

    def _should_handle_header_drag(self, local_pos: QPoint) -> bool:
        child = self.childAt(local_pos)
        return not isinstance(child, MTButton)
