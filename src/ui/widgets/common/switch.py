from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen, QResizeEvent
from PySide6.QtWidgets import QCheckBox, QWidget

from src.ui.theme.colors import to_qcolor
from src.ui.painting import new_widget_painter
from src.ui.widgets.paint_primitives import parse_non_negative_float, parse_pen_style, resolve_fill_brush, resolve_uniform_radius, rounded_rect_path
from src.utils.qt import build_object_name

from .widget import MTWidget


class MTSwitch(QCheckBox):
    _track: MTWidget | None = None
    _handle: MTWidget | None = None
    
    _OBJECT_NAME = 'Switch'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str = '',
        obj_name: tuple[str, ...] = (),
        checked: bool = False,
    ) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setChecked(checked)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))

        self._margin = 3
        self._syncing_visuals = False
        self._checked_state_cache: bool | None = None
        self._visual_checked_state = bool(checked)
        self._pending_visual_checked_state: bool | None = None
        self._visual_sync_queued = False
        self._checked_color = QColor(Qt.GlobalColor.transparent)
        self._unchecked_color = QColor(Qt.GlobalColor.transparent)
        self._handle_color = QColor(Qt.GlobalColor.transparent)
        self._checked_handle_color: QColor | None = None
        self._unchecked_handle_color: QColor | None = None
        self._track_border_rule = ''
        self._handle_border_rule = ''
        self._track_radius = '0px'
        self._handle_radius = '0px'
        self._default_size = (40, 20)
        self._animated_handle_color: QColor | None = None

        self._track = MTWidget(self)
        self._track.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._track.setProperty('part', 'track')
        self._track.hide()

        self._handle = MTWidget(self)
        self._handle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._handle.setProperty('part', 'handle')
        self._handle.hide()

        self.toggled.connect(self._on_toggled)
        
        self.setFixedSize(*self._default_size)
        
        self._sync_visuals()

    def sync_size(self, *, bounds_width: int | None = None, bounds_height: int | None = None) -> None:
        self.setFixedSize(*self._default_size)
        self._sync_visuals()

    def setChecked(self, checked: bool) -> None:
        previous = self.isChecked()
        super().setChecked(bool(checked))
        current = self.isChecked()
        if previous != current:
            if self.signalsBlocked():
                self._sync_visuals()
            return
        return

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_visuals()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if self._track is None or self._handle is None:
            return
        if self._syncing_visuals:
            return
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.EnabledChange,
        ):
            self._sync_visuals(sync_state_props=False)

    def _on_toggled(self, _: bool) -> None:
        self._sync_checked_properties()
        self._queue_visual_state_sync(self.isChecked())

    def _sync_visuals(self, *, animate: bool = False, sync_state_props: bool = True) -> None:
        _ = animate
        if self._syncing_visuals:
            return

        self._syncing_visuals = True
        try:
            if sync_state_props:
                self._sync_checked_properties()
            self._visual_checked_state = self.isChecked()
            self._pending_visual_checked_state = None
            self.update()
        finally:
            self._syncing_visuals = False

    def _queue_visual_state_sync(self, checked: bool) -> None:
        self._pending_visual_checked_state = bool(checked)
        if self._visual_sync_queued:
            return
        self._visual_sync_queued = True
        QTimer.singleShot(0, self._flush_queued_visual_state)

    def _flush_queued_visual_state(self) -> None:
        self._visual_sync_queued = False
        pending = self._pending_visual_checked_state
        self._pending_visual_checked_state = None
        if pending is None:
            return
        self._visual_checked_state = bool(pending)
        self.update()

    def _visual_checked(self) -> bool:
        return bool(self._visual_checked_state)

    def _part_key(self, part: str) -> str | None:
        part_key = str(part).strip()
        return part_key if part_key in {'handle', 'track'} else None

    def _part_state_color(self, part: str, checked: bool) -> QColor | None:
        if part == 'handle':
            if isinstance(self._animated_handle_color, QColor) and self._animated_handle_color.isValid():
                return QColor(self._animated_handle_color)
            state_color = self._checked_handle_color if checked else self._unchecked_handle_color
            if isinstance(state_color, QColor) and state_color.isValid():
                return QColor(state_color)
            return QColor(self._handle_color) if self._handle_color.isValid() else None
        color = self._checked_color if checked else self._unchecked_color
        return QColor(color) if color.isValid() else None

    def current_part_color(self, part: str) -> QColor | None:
        part_key = self._part_key(part)
        if part_key is None:
            return None
        return self._part_state_color(part_key, self._visual_checked())

    def set_part_color(self, part: str, value: object) -> bool:
        color = to_qcolor(value)
        if color is None:
            return False

        part_key = self._part_key(part)
        if part_key is None:
            return False

        base_color = QColor(color)
        if part_key == 'handle':
            self._handle_color = QColor(base_color)
            self._checked_handle_color = None
            self._unchecked_handle_color = None
            self._animated_handle_color = QColor(base_color)
        else:
            self._checked_color = QColor(base_color)
            self._unchecked_color = QColor(base_color)

        self.update()
        return True

    def set_part_style_value(self, part: str, path: tuple[str, ...], value: object) -> bool:
        if path in {('color',), ('background', 'color')}:
            return self.set_part_color(part, value)
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        _ = event
        painter = new_widget_painter(self, smooth_pixmap=True)

        track_rect = QRectF(self.rect())
        handle_rect = self._handle_rect()
        self._draw_part(painter, track_rect, 'track')
        self._draw_part(painter, handle_rect, 'handle')
        painter.end()

    def _handle_rect(self) -> QRectF:
        rect = QRectF(self.rect())
        handle_size = max(0.0, rect.height() - (self._margin * 2.0))
        y = rect.top() + max(0.0, (rect.height() - handle_size) / 2.0)
        x_off = rect.left() + self._margin
        x_on = rect.right() - self._margin - handle_size
        x = x_on if self._visual_checked() else x_off
        return QRectF(x, y, handle_size, handle_size)

    def _draw_part(self, painter: QPainter, rect: QRectF, part: str) -> None:
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
            return
        part_key = self._part_key(part)
        if part_key is None:
            return

        painter.save()
        painter.setBrush(self._part_brush(part_key, rect))

        border_rule = self._handle_border_rule if part_key == 'handle' else self._track_border_rule
        border_width, border_style, border_color = self._parse_border_rule(border_rule)
        if border_width > 0.0 and border_style != Qt.PenStyle.NoPen and border_color.isValid():
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        radius_value = self._handle_radius if part_key == 'handle' else self._track_radius
        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        painter.drawPath(rounded_rect_path(draw_rect, resolve_uniform_radius(draw_rect, radius_value)))
        painter.restore()

    def _part_brush(self, part: str, rect: QRectF) -> QColor | Qt.BrushStyle | object:
        return resolve_fill_brush(
            rect,
            color=self.current_part_color(part),
        )

    def _parse_border_rule(self, rule: str) -> tuple[float, Qt.PenStyle, QColor]:
        text = str(rule or '').strip()
        if not text.startswith('border:'):
            return 0.0, Qt.PenStyle.NoPen, QColor()

        value = text.removeprefix('border:').strip().rstrip(';').strip()
        parts = [part for part in value.split() if part]
        if len(parts) < 3:
            return 0.0, Qt.PenStyle.NoPen, QColor()

        width = parse_non_negative_float(parts[0])
        style = parse_pen_style(parts[1])
        color = to_qcolor(' '.join(parts[2:]))
        return width, style, color if color is not None else QColor()

    def _sync_checked_properties(self) -> None:
        checked = self.isChecked()
        if self._checked_state_cache is checked:
            return

        track = self._track
        handle = self._handle
        if track is None or handle is None:
            return

        self._checked_state_cache = checked
        checked_value = 'true' if checked else 'false'
        for widget in (self, track, handle):
            widget.setProperty('checked', checked_value)
            if widget.property('unchecked') is not None:
                widget.setProperty('unchecked', None)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
