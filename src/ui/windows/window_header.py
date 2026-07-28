from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QIcon, QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QApplication, QBoxLayout, QSizePolicy, QWidget

from src.app.paths import PATH_HEADER_ICONS_SRC
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import MTButton, MTPlainLabel, MTWidget

_HEADER_RESIZE_MARGIN = 8
_HEADER_OBJECT_NAME = 'Main_Window_Header'
_QT_MAX_SIZE = 16_777_215


class _HeaderIconButton(MTButton):
    def __init__(self, icon_name: str) -> None:
        button_name = '_'.join(
            part.capitalize() for part in icon_name.split('_')
        )
        super().__init__(
            tr_key='',
            obj_name=f'{_HEADER_OBJECT_NAME}_{button_name}_Button',
        )
        self.setText('')
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumSize(18, 18)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_icon_by_name(icon_name)

    def set_icon_by_name(self, icon_name: str) -> None:
        icon_path = PATH_HEADER_ICONS_SRC / f'{icon_name}.svg'
        icon = QIcon(str(icon_path))
        if icon.isNull():
            self.setIcon(QIcon())
            return
        self.setIcon(icon)
        self.setIconSize(QSize(14, 14))


class _HeaderTitleLabel(MTPlainLabel):
    def __init__(
        self,
        text: str = '',
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
    ) -> None:
        super().__init__(text, parent, obj_name=obj_name)

    def setAlignment(self, alignment: Qt.AlignmentFlag) -> None:
        super().setAlignment(alignment)
        parent = self.parentWidget()
        if isinstance(parent, MTWindowHeader):
            parent.sync_title_geometry()


class _HeaderResizeGrip(QWidget):
    def __init__(
        self,
        header: 'MTWindowHeader',
        edges: Qt.Edge,
        *,
        obj_name: str,
        cursor: Qt.CursorShape,
    ) -> None:
        super().__init__(header.window())
        self._header = header
        self._edges = edges
        self.setObjectName(obj_name)
        self.setMouseTracking(True)
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._header.begin_resize(self._edges, event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._header.update_manual_resize(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._header.finish_manual_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class MTWindowHeader(MTWidget):
    def __init__(
        self,
        window: QWidget,
        *,
        title: str | None = None,
    ) -> None:
        super().__init__(parent=window, obj_name=_HEADER_OBJECT_NAME)
        self._window = window
        self._resize_margin = _HEADER_RESIZE_MARGIN
        self._drag_press_pos = QPoint()
        self._maximized_drag_pending = False
        self._manual_move_active = False
        self._manual_move_offset = QPoint()
        self._manual_resize_active = False
        self._manual_resize_edges: Qt.Edge | None = None
        self._manual_resize_start_global = QPoint()
        self._manual_resize_start_geometry = QRect()
        self._buttons_host: MTWidget | None = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        layout = create_layout(LayoutType.HBOX, parent=self)

        self._title_label = _HeaderTitleLabel(
            title or window.windowTitle(),
            self,
            obj_name=f'{_HEADER_OBJECT_NAME}_Title',
        )
        self._title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        layout.addStretch(1)

        self._buttons_host = MTWidget(
            parent=self,
            obj_name=f'{_HEADER_OBJECT_NAME}_Buttons',
        )
        self._buttons_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._buttons_host.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        buttons_layout = create_layout(LayoutType.HBOX, parent=self._buttons_host)
        layout.addWidget(self._buttons_host)

        self._minimize_button = _HeaderIconButton('minimize')
        self._minimize_button.clicked.connect(self._window.showMinimized)
        buttons_layout.addWidget(self._minimize_button)

        self._maximize_button = _HeaderIconButton('maximize')
        self._maximize_button.clicked.connect(self._toggle_maximized)
        buttons_layout.addWidget(self._maximize_button)

        self._close_button = _HeaderIconButton('close')
        self._close_button.clicked.connect(self._window.close)
        buttons_layout.addWidget(self._close_button)

        self._window.installEventFilter(self)
        self._resize_grips = self._create_resize_grips()
        self.sync_window_meta()
        self.sync_title_geometry()
        self._sync_resize_grips()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._window:
            match event.type():
                case QEvent.Type.Show | QEvent.Type.Resize:
                    self._sync_resize_grips()
                case QEvent.Type.WindowTitleChange | QEvent.Type.WindowStateChange:
                    self.sync_window_meta()
                    self._manual_move_active = False
                    self._maximized_drag_pending = False
                    self.finish_manual_resize()
                    self._sync_resize_grips()
                case QEvent.Type.Close:
                    self.finish_manual_resize()
                case _:
                    pass
        return super().eventFilter(obj, event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.sync_title_geometry()
        if self._buttons_host is not None:
            self._buttons_host.raise_()

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

    def set_header_title(self, title: str) -> None:
        self._title_label.setText(str(title or ''))

    def sync_window_meta(self) -> None:
        self._title_label.setText(self._window.windowTitle())
        self._maximize_button.set_icon_by_name(
            'restore' if self._window.isMaximized() else 'maximize'
        )
        self.sync_title_geometry()

    def begin_resize(self, edges: Qt.Edge, global_pos: QPoint) -> None:
        if self._window.isMaximized() or self._window.isFullScreen():
            return
        if self._start_system_resize(edges):
            return
        self._manual_resize_active = True
        self._manual_resize_edges = edges
        self._manual_resize_start_global = QPoint(global_pos)
        self._manual_resize_start_geometry = QRect(self._window.geometry())

    def update_manual_resize(self, global_pos: QPoint) -> None:
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

    def finish_manual_resize(self) -> None:
        self._manual_resize_active = False
        self._manual_resize_edges = None

    def _toggle_maximized(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_window_meta()
        self._sync_resize_grips()

    def _restore_from_maximized_drag(self, global_pos: QPoint) -> None:
        old_width = max(1, self._window.width())
        press_ratio = max(0.0, min(1.0, self._drag_press_pos.x() / old_width))

        normal_geometry = self._window.normalGeometry()
        restored_width = max(1, normal_geometry.width() or self._window.width())
        restored_height = max(1, normal_geometry.height() or self._window.height())
        target_x = global_pos.x() - int(round(restored_width * press_ratio))
        target_y = global_pos.y() - min(
            self._drag_press_pos.y(), max(0, restored_height - 1)
        )

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

    def _create_resize_grips(self) -> list[_HeaderResizeGrip]:
        obj_name = _HEADER_OBJECT_NAME
        grips = [
            _HeaderResizeGrip(
                self,
                Qt.Edge.LeftEdge,
                obj_name=f'{obj_name}_Resize_Left_Grip',
                cursor=Qt.CursorShape.SizeHorCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.RightEdge,
                obj_name=f'{obj_name}_Resize_Right_Grip',
                cursor=Qt.CursorShape.SizeHorCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.TopEdge,
                obj_name=f'{obj_name}_Resize_Top_Grip',
                cursor=Qt.CursorShape.SizeVerCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.BottomEdge,
                obj_name=f'{obj_name}_Resize_Bottom_Grip',
                cursor=Qt.CursorShape.SizeVerCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
                obj_name=f'{obj_name}_Resize_Top_Left_Grip',
                cursor=Qt.CursorShape.SizeFDiagCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.TopEdge | Qt.Edge.RightEdge,
                obj_name=f'{obj_name}_Resize_Top_Right_Grip',
                cursor=Qt.CursorShape.SizeBDiagCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
                obj_name=f'{obj_name}_Resize_Bottom_Left_Grip',
                cursor=Qt.CursorShape.SizeBDiagCursor,
            ),
            _HeaderResizeGrip(
                self,
                Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
                obj_name=f'{obj_name}_Resize_Bottom_Right_Grip',
                cursor=Qt.CursorShape.SizeFDiagCursor,
            ),
        ]
        for grip in grips:
            grip.hide()
        return grips

    def _sync_resize_grips(self) -> None:
        if not self._window.isVisible():
            return

        margin = max(1, int(self._resize_margin))
        rect = self._window.rect()
        width = max(0, rect.width())
        height = max(0, rect.height())
        enabled = not (self._window.isMaximized() or self._window.isFullScreen())

        geometries = [
            QRect(0, margin, margin, max(0, height - (margin * 2))),
            QRect(max(0, width - margin), margin, margin, max(0, height - (margin * 2))),
            QRect(margin, 0, max(0, width - (margin * 2)), margin),
            QRect(margin, max(0, height - margin), max(0, width - (margin * 2)), margin),
            QRect(0, 0, margin, margin),
            QRect(max(0, width - margin), 0, margin, margin),
            QRect(0, max(0, height - margin), margin, margin),
            QRect(max(0, width - margin), max(0, height - margin), margin, margin),
        ]

        for grip, geometry in zip(self._resize_grips, geometries, strict=False):
            grip.setGeometry(geometry)
            if enabled:
                grip.show()
                grip.raise_()
            else:
                grip.hide()

    def sync_title_geometry(self) -> None:
        if self._buttons_host is None:
            return
        right_reserved = max(0, self._buttons_host.width())
        alignment = self._title_label.alignment()
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            x = right_reserved
            width = max(0, self.width() - (right_reserved * 2))
        else:
            x = 0
            width = max(0, self.width() - right_reserved)
        self._title_label.setGeometry(QRect(x, 0, width, self.height()))


def apply_frameless_window_header(
    window: QWidget,
    layout: QBoxLayout,
    *,
    title: str | None = None,
) -> MTWindowHeader:
    window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    window.setWindowFlag(Qt.WindowType.Window, True)
    header = MTWindowHeader(window, title=title)
    layout.insertWidget(0, header)
    return header
