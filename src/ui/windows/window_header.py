from __future__ import annotations

import sys
from time import monotonic
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter, QEvent, QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QFontMetricsF, QIcon, QLinearGradient, QMouseEvent, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import MTButton, MTPlainLabel, MTWidget
from src.theme.rainbow.palette import sample_rainbow_color
from src.utils.constants import PATH_HEADER_ICONS

if sys.platform.startswith('win'):
    import ctypes
    from ctypes import wintypes

    GWL_STYLE = -16
    WM_NCHITTEST = 0x0084
    HTCLIENT = 1
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17
    HTCAPTION = 2
    GA_ROOT = 2
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    LONG_PTR = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    MSG = wintypes.MSG

    _USER32 = ctypes.windll.user32
    _USER32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    _USER32.GetAncestor.restype = wintypes.HWND
    _USER32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    _USER32.GetWindowLongPtrW.restype = LONG_PTR
    _USER32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
    _USER32.SetWindowLongPtrW.restype = LONG_PTR
    _USER32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    _USER32.SetWindowPos.restype = wintypes.BOOL


class _FramelessWindowNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self) -> None:
        super().__init__()
        self._headers: dict[int, MTWindowHeader] = {}

    def register(self, header: MTWindowHeader) -> None:
        try:
            handle = int(header.window().winId())
        except RuntimeError:
            return
        self._headers[handle] = header

    def unregister(self, header: MTWindowHeader) -> None:
        stale_handles = [handle for handle, item in self._headers.items() if item is header]
        for handle in stale_handles:
            self._headers.pop(handle, None)

    def nativeEventFilter(self, event_type, message):
        if not sys.platform.startswith('win'):
            return False, 0

        try:
            msg = MSG.from_address(int(message))
        except (TypeError, ValueError, OSError):
            return False, 0

        if msg.hWnd is None:
            return False, 0

        hwnd = int(msg.hWnd)
        header = self._headers.get(hwnd)
        if header is None:
            root_hwnd = _USER32.GetAncestor(hwnd, GA_ROOT)
            if root_hwnd:
                header = self._headers.get(int(root_hwnd))
        if header is None:
            return False, 0

        if msg.message == WM_NCHITTEST:
            result = header.native_hit_test(int(msg.lParam))
            if result is None:
                return False, 0
            return True, int(result)

        return False, 0


_NATIVE_EVENT_FILTER: _FramelessWindowNativeEventFilter | None = None


def _enable_native_resize_frame(window: QWidget) -> None:
    if not sys.platform.startswith('win'):
        return

    hwnd = int(window.winId())
    style = int(_USER32.GetWindowLongPtrW(hwnd, GWL_STYLE))
    resizable_style = style | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
    if resizable_style != style:
        _USER32.SetWindowLongPtrW(hwnd, GWL_STYLE, resizable_style)
    _USER32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
    )


def _install_native_event_filter() -> _FramelessWindowNativeEventFilter | None:
    global _NATIVE_EVENT_FILTER
    if not sys.platform.startswith('win'):
        return None
    if _NATIVE_EVENT_FILTER is not None:
        return _NATIVE_EVENT_FILTER
    app = QApplication.instance()
    if app is None:
        return None
    _NATIVE_EVENT_FILTER = _FramelessWindowNativeEventFilter()
    app.installNativeEventFilter(_NATIVE_EVENT_FILTER)
    return _NATIVE_EVENT_FILTER


def _header_icon(name: str) -> QIcon:
    path = PATH_HEADER_ICONS / f'{name}.svg'
    return QIcon(str(path)) if isinstance(path, Path) and path.exists() else QIcon()


class _HeaderIconButton(MTButton):
    def __init__(self, *, obj_name: str, icon_name: str) -> None:
        super().__init__(tr_key='', obj_name=obj_name)
        self.setProperty('rainbowBorderExcluded', True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIcon(_header_icon(icon_name))
        self.setIconSize(QSize(14, 14))
        self.setMinimumSize(18, 18)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_icon_by_name(self, icon_name: str) -> None:
        self.setIcon(_header_icon(icon_name))


class _HeaderTitleLabel(MTPlainLabel):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_force_text_path_render(True)
        self._ribbon_enabled = False
        self._ribbon_duration_ms = 5000
        self._ribbon_palette = 'Classic'
        self._ribbon_saturation = 1.0
        self._ribbon_epoch = monotonic()
        self._ribbon_timer = QTimer(self)
        self._ribbon_timer.setInterval(16)
        self._ribbon_timer.timeout.connect(self.update)

    def setAlignment(self, alignment: Qt.AlignmentFlag) -> None:
        super().setAlignment(alignment)
        if (parent := self.parentWidget()) is not None:
            sync = getattr(parent, '_sync_title_geometry', None)
            if callable(sync) and hasattr(parent, '_buttons_host'):
                sync()

    def set_rainbow_enabled(self, enabled: bool, duration_ms: int | float, saturation: float = 0.6, palette: str = 'Classic') -> None:
        was_enabled = self._ribbon_enabled
        previous_phase = self._phase() if was_enabled else 0.0
        self._ribbon_enabled = bool(enabled)
        self._ribbon_duration_ms = max(1, int(round(float(duration_ms))))
        self._ribbon_palette = str(palette).strip() or 'Classic'
        self._ribbon_saturation = max(0.0, min(float(saturation), 1.0))
        self._ribbon_epoch = monotonic() - ((previous_phase * float(self._ribbon_duration_ms)) / 1000.0)
        if self._ribbon_enabled:
            if not self._ribbon_timer.isActive():
                self._ribbon_timer.start()
        else:
            self._ribbon_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(self.font())

        if self.has_box_theme():
            self.draw_box_theme(painter)
        else:
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

        text = self.text()
        if not text.strip():
            painter.end()
            return

        rect = QRectF(self.contentsRect())
        if not self._ribbon_enabled:
            self._draw_themed_icon_text(
                painter,
                rect,
                self.alignment(),
                text,
                self.palette().windowText().color(),
            )
            painter.end()
            return

        metrics = QFontMetricsF(self.font())
        baseline_y = self._text_baseline_y(rect, metrics)
        path = QPainterPath()
        path.addText(0.0, baseline_y, self.font(), text)
        path_bounds = path.boundingRect()

        if path_bounds.isEmpty():
            painter.end()
            return

        text_left = self._text_left(rect, metrics.horizontalAdvance(text))
        path.translate(text_left - path_bounds.left(), 0.0)
        path_bounds = path.boundingRect()

        phase = self._phase()
        gradient = QLinearGradient(
            path_bounds.left(),
            rect.center().y(),
            path_bounds.right(),
            rect.center().y(),
        )
        sample_count = 48
        for sample_index in range(sample_count + 1):
            offset = sample_index / sample_count
            gradient.setColorAt(
                offset,
                sample_rainbow_color(
                    offset - phase,
                    palette=self._ribbon_palette,
                    saturation=self._ribbon_saturation,
                ),
            )

        border = getattr(self, '_text_border', None)
        if isinstance(border, dict):
            border_color = border.get('color')
            border_width = float(border.get('width', 0.0) or 0.0)
            border_style = self._pen_style(border.get('style', 'solid'))
            if border_color is not None and border_color.isValid() and border_color.alpha() > 0 and border_width > 0.0 and border_style != Qt.PenStyle.NoPen:
                self._draw_text_outline(
                    painter,
                    path,
                    fill=QBrush(gradient),
                    border_color=border_color,
                    border_width=border_width,
                    border_style=border_style,
                )
                painter.end()
                return

        painter.fillPath(path, gradient)
        painter.end()

    def _text_left(self, rect: QRectF, text_width: float) -> float:
        alignment = self.alignment()
        if alignment & Qt.AlignmentFlag.AlignRight:
            return rect.right() - text_width
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            return rect.left() + ((rect.width() - text_width) / 2.0)
        return rect.left()

    def _text_baseline_y(self, rect: QRectF, metrics: QFontMetricsF) -> float:
        alignment = self.alignment()
        if alignment & Qt.AlignmentFlag.AlignTop:
            return rect.top() + metrics.ascent()
        if alignment & Qt.AlignmentFlag.AlignBottom:
            return rect.bottom() - metrics.descent()
        return rect.y() + ((rect.height() - metrics.height()) / 2.0) + metrics.ascent()

    def _phase(self) -> float:
        elapsed_ms = (monotonic() - self._ribbon_epoch) * 1000.0
        return (elapsed_ms % float(self._ribbon_duration_ms)) / float(self._ribbon_duration_ms)


class MTWindowHeader(MTWidget):
    def __init__(
        self,
        window: QWidget,
        *,
        title: str | None = None,
        allow_minimize: bool = True,
        allow_maximize: bool = True,
        obj_name: str = 'Window_Header',
    ) -> None:
        super().__init__(parent=window, obj_name=obj_name)
        self._window = window
        self._resize_border = 2
        self._resize_border_over_header_buttons = 0
        self._maximized_drag_pending = False
        self._drag_press_pos = QPoint()
        self._native_filter = _install_native_event_filter()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = create_layout(LayoutType.HBOX, parent=self)

        self._title_label = _HeaderTitleLabel(title or window.windowTitle(), self, obj_name=f'{obj_name}_Title')
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addStretch(1)

        self._buttons_host = MTWidget(parent=self, obj_name=f'{obj_name}_Buttons')
        self._buttons_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._buttons_host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        buttons_layout = create_layout(LayoutType.HBOX, parent=self._buttons_host)
        layout.addWidget(self._buttons_host)

        self._minimize_button: _HeaderIconButton | None = None
        self._maximize_button: _HeaderIconButton | None = None

        if allow_minimize:
            self._minimize_button = _HeaderIconButton(
                obj_name=f'{obj_name}_Minimize_Button',
                icon_name='roll_up',
            )
            self._minimize_button.clicked.connect(self._window.showMinimized)
            buttons_layout.addWidget(self._minimize_button)

        if allow_maximize:
            self._maximize_button = _HeaderIconButton(
                obj_name=f'{obj_name}_Maximize_Button',
                icon_name='maximize',
            )
            self._maximize_button.clicked.connect(self._toggle_maximized)
            buttons_layout.addWidget(self._maximize_button)

        self._close_button = _HeaderIconButton(
            obj_name=f'{obj_name}_Close_Button',
            icon_name='close',
        )
        self._close_button.clicked.connect(self._window.close)
        buttons_layout.addWidget(self._close_button)

        _enable_native_resize_frame(window)
        window.installEventFilter(self)
        if self._native_filter is not None:
            self._native_filter.register(self)
        window.destroyed.connect(lambda *_: self._unregister_native_filter())
        self.sync_window_meta()
        self._sync_title_geometry()

    def eventFilter(self, obj, event: QEvent):
        if obj is self._window and event.type() in {
            QEvent.Type.Show,
            QEvent.Type.WinIdChange,
        }:
            _enable_native_resize_frame(self._window)
            if self._native_filter is not None:
                self._native_filter.register(self)

        if obj is self._window:
            if event.type() == QEvent.Type.Close:
                self._unregister_native_filter()
            if event.type() in {
                QEvent.Type.WindowTitleChange,
                QEvent.Type.WindowStateChange,
            }:
                self.sync_window_meta()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_title_geometry()
        self._buttons_host.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._should_handle_header_drag(event.position().toPoint()):
            self._maximized_drag_pending = self._window.isMaximized()
            self._drag_press_pos = event.position().toPoint()
        else:
            self._maximized_drag_pending = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._maximized_drag_pending and
            (event.buttons() & Qt.MouseButton.LeftButton) and
            self._should_handle_header_drag(event.position().toPoint())
        ):
            moved = event.position().toPoint() - self._drag_press_pos
            if moved.manhattanLength() >= QApplication.startDragDistance():
                self._restore_from_maximized_drag(event)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._maximized_drag_pending = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton and
            self._should_handle_header_drag(event.position().toPoint())
        ):
            if sys.platform.startswith('win') and self._native_filter is not None:
                event.ignore()
                return
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def set_header_title(self, title: str) -> None:
        self._title_label.setText(str(title or ''))

    def set_title_rainbow(self, enabled: bool, duration_ms: int | float, palette: str = 'Classic') -> None:
        self._title_label.set_rainbow_enabled(bool(enabled), duration_ms, palette=palette)

    def sync_window_meta(self) -> None:
        self._title_label.setText(self._window.windowTitle())

        if self._maximize_button is not None:
            is_maximized = self._window.isMaximized()
            self._maximize_button.set_icon_by_name('minimize' if is_maximized else 'maximize')

    def _toggle_maximized(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_window_meta()

    def _restore_from_maximized_drag(self, event: QMouseEvent) -> None:
        global_pos = event.globalPosition().toPoint()
        old_width = max(1, self._window.width())
        press_ratio = max(0.0, min(1.0, self._drag_press_pos.x() / old_width))

        normal_geometry = self._window.normalGeometry()
        restored_width = max(1, normal_geometry.width() or self._window.width())
        restored_height = max(1, normal_geometry.height() or self._window.height())
        target_x = global_pos.x() - int(round(restored_width * press_ratio))
        target_y = global_pos.y() - min(self._drag_press_pos.y(), max(0, restored_height - 1))

        if (screen := QApplication.screenAt(global_pos)) is not None:
            available = screen.availableGeometry()
            max_x = max(available.left(), available.right() - restored_width + 1)
            max_y = max(available.top(), available.bottom() - restored_height + 1)
            target_x = max(available.left(), min(target_x, max_x))
            target_y = max(available.top(), min(target_y, max_y))

        self._window.showNormal()
        self.sync_window_meta()
        self._window.move(target_x, target_y)

        self._maximized_drag_pending = False
        if (handle := self._window.windowHandle()) is not None:
            handle.startSystemMove()

    def _unregister_native_filter(self) -> None:
        if self._native_filter is None:
            return
        self._native_filter.unregister(self)

    def native_hit_test(self, lparam: int) -> int | None:
        if not sys.platform.startswith('win'):
            return None
        if not self._window.isVisible():
            return None

        global_pos = self._global_pos_from_lparam(lparam)
        if global_pos is None:
            return None

        if (edge_hit := self._hit_test_resize_edges(global_pos)) is not None:
            return edge_hit

        if self._is_over_interactive_widget(global_pos):
            return HTCLIENT

        if (header_hit := self._hit_test_header(global_pos)) is not None:
            return header_hit

        return None

    def _global_pos_from_lparam(self, lparam: int) -> QPoint | None:
        x = ctypes.c_short(lparam & 0xFFFF).value if sys.platform.startswith('win') else 0
        y = ctypes.c_short((lparam >> 16) & 0xFFFF).value if sys.platform.startswith('win') else 0
        return QPoint(int(x), int(y))

    def _is_over_interactive_widget(self, global_pos: QPoint) -> bool:
        local_pos = self._window.mapFromGlobal(global_pos)
        if not self._window.rect().contains(local_pos):
            return False

        child = self._window.childAt(local_pos)
        while child is not None:
            if isinstance(child, (QAbstractButton, QLineEdit, QAbstractSpinBox, QComboBox, QAbstractSlider)):
                return True
            child = child.parentWidget()
        return False

    def _hit_test_resize_edges(self, global_pos: QPoint) -> int | None:
        edges = self._resize_edges_at(global_pos)
        if edges is None:
            return None

        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)

        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        return None

    def _resize_edges_at(self, global_pos: QPoint):
        if self._window.isMaximized() or self._window.isFullScreen():
            return None

        local_pos = self._window.mapFromGlobal(global_pos)
        rect = self._window.rect()
        if not rect.contains(local_pos):
            return None

        border = self._resize_border_for_position(global_pos)
        left = local_pos.x() <= border
        right = local_pos.x() >= rect.width() - border - 1
        top = local_pos.y() <= border
        bottom = local_pos.y() >= rect.height() - border - 1

        edges = None
        if left:
            edges = Qt.Edge.LeftEdge
        elif right:
            edges = Qt.Edge.RightEdge

        if top:
            edges = Qt.Edge.TopEdge if edges is None else edges | Qt.Edge.TopEdge
        elif bottom:
            edges = Qt.Edge.BottomEdge if edges is None else edges | Qt.Edge.BottomEdge

        return edges

    def _resize_border_for_position(self, global_pos: QPoint) -> int:
        if self._point_in_widget(self._buttons_host, global_pos):
            return max(0, int(self._resize_border_over_header_buttons))
        return max(0, int(self._resize_border))

    def _hit_test_header(self, global_pos: QPoint) -> int | None:
        if not self.isVisible():
            return None

        local_pos = self.mapFromGlobal(global_pos)
        if not self.rect().contains(local_pos):
            return None

        if self._point_in_widget(self._buttons_host, global_pos):
            return HTCLIENT

        if self._window.isMaximized():
            return HTCLIENT

        return HTCAPTION

    def _should_handle_header_drag(self, local_pos: QPoint) -> bool:
        child = self.childAt(local_pos)
        if isinstance(child, QAbstractButton):
            return False
        return True

    def _sync_title_geometry(self) -> None:
        right_reserved = max(0, self._buttons_host.width())
        alignment = self._title_label.alignment()
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            x = right_reserved
            width = max(0, self.width() - (right_reserved * 2))
        else:
            x = 0
            width = max(0, self.width() - right_reserved)
        self._title_label.setGeometry(QRect(x, 0, width, self.height()))

    @staticmethod
    def _point_in_widget(widget: QWidget | None, global_pos: QPoint) -> bool:
        if widget is None or not widget.isVisible():
            return False
        local_pos = widget.mapFromGlobal(global_pos)
        return widget.rect().contains(local_pos)


def apply_frameless_window_header(
    window: QWidget,
    layout: QHBoxLayout | QVBoxLayout | QGridLayout | object,
    *,
    title: str | None = None,
    allow_minimize: bool = True,
    allow_maximize: bool = True,
    obj_name: str = 'Window_Header',
) -> MTWindowHeader:
    window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    window.setWindowFlag(Qt.WindowType.Window, True)
    header = MTWindowHeader(
        window,
        title=title,
        allow_minimize=allow_minimize,
        allow_maximize=allow_maximize,
        obj_name=obj_name,
    )
    layout.insertWidget(0, header)
    return header
