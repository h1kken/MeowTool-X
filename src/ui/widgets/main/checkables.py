from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPen, QResizeEvent
from PySide6.QtWidgets import QCheckBox, QSizePolicy, QWidget

from src.theme.colors import to_qcolor
from src.theme.schema.access import coerce_positive_int, theme_map
from src.ui.painting import new_widget_painter
from src.ui.widgets.main.containers import MTWidget
from src.ui.widgets.main.paint_primitives import (
    parse_non_negative_float,
    parse_pen_style,
    resolve_fill_brush,
    resolve_uniform_radius,
    rounded_rect_path,
)
from src.ui.widgets.types import WidgetThemeMap


class MTSwitch(QCheckBox):
    _track: MTWidget | None = None
    _handle: MTWidget | None = None

    def __init__(
        self,
        text: str = '',
        checked: bool = False,
        obj_name: str = '',
        checked_color: str | None = None,
        unchecked_color: str | None = None,
        handle_color: str | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setText('')

        self._margin = 3
        self._syncing_visuals = False
        self._checked_state_cache: bool | None = None
        self._visual_checked_state = bool(checked)
        self._pending_visual_checked_state: bool | None = None
        self._visual_sync_queued = False
        self._checked_color = self._resolve_initial_color(checked_color, QColor(Qt.GlobalColor.transparent))
        self._unchecked_color = self._resolve_initial_color(unchecked_color, QColor(Qt.GlobalColor.transparent))
        self._handle_color = self._resolve_initial_color(handle_color, QColor(Qt.GlobalColor.transparent))
        self._checked_handle_color: QColor | None = None
        self._unchecked_handle_color: QColor | None = None
        self._default_margin = self._margin
        self._default_checked_color = QColor(self._checked_color)
        self._default_unchecked_color = QColor(self._unchecked_color)
        self._default_handle_color = QColor(self._handle_color)
        self._track_border_rule = ''
        self._handle_border_rule = ''
        self._track_radius = '0px'
        self._handle_radius = '0px'
        self._default_size = (40, 20)
        self._theme_fixed_size: tuple[int, int] | None = None
        self._animated_handle_color: QColor | None = None

        self._track = MTWidget(parent=self)
        self._track.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._track.setProperty('switchPart', 'track')
        self._track.hide()

        self._handle = MTWidget(parent=self)
        self._handle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._handle.setProperty('switchPart', 'handle')
        self._handle.hide()

        self.toggled.connect(self._on_toggled)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(*self._default_size)

        if obj_name:
            self.setObjectName(obj_name)

        self.setChecked(checked)
        self._sync_visuals()

    def sync_size(self, *, bounds_width: int | None = None, bounds_height: int | None = None) -> None:
        target_size = self._theme_fixed_size or self._default_size
        self.setFixedSize(*target_size)
        self._sync_visuals()

    def _resolve_initial_color(self, value: str | None, fallback: QColor) -> QColor:
        if isinstance(value, str) and value.strip():
            color = to_qcolor(value)
            if color is not None:
                return color
        return QColor(fallback)

    def reset_theme(self) -> None:
        self._margin = self._default_margin
        self._checked_color = QColor(self._default_checked_color)
        self._unchecked_color = QColor(self._default_unchecked_color)
        self._handle_color = QColor(self._default_handle_color)
        self._checked_handle_color = None
        self._unchecked_handle_color = None
        self._animated_handle_color = None
        self._track_border_rule = ''
        self._handle_border_rule = ''
        self._track_radius = '0px'
        self._handle_radius = '0px'
        self._theme_fixed_size = None
        self.setFixedSize(*self._default_size)
        self._sync_visuals()

    def apply_theme(self, data: WidgetThemeMap) -> None:
        track_data = theme_map(data.get('track'))
        if track_data is not None:
            self._track_border_rule, self._track_radius = self._part_frame_rules(track_data)
            checked_data = theme_map(track_data.get('checked')) or {}
            unchecked_data = theme_map(track_data.get('unchecked')) or {}
            checked_background = theme_map(checked_data.get('background')) or {}
            unchecked_background = theme_map(unchecked_data.get('background')) or {}
            checked_color = checked_data.get('color')
            if isinstance(checked_color, str):
                color = to_qcolor(checked_color)
                if color is not None:
                    self._checked_color = color
            checked_bg_color = checked_background.get('color')
            if isinstance(checked_bg_color, str):
                color = to_qcolor(checked_bg_color)
                if color is not None:
                    self._checked_color = color
            unchecked_color = unchecked_data.get('color')
            if isinstance(unchecked_color, str):
                color = to_qcolor(unchecked_color)
                if color is not None:
                    self._unchecked_color = color
            unchecked_bg_color = unchecked_background.get('color')
            if isinstance(unchecked_bg_color, str):
                color = to_qcolor(unchecked_bg_color)
                if color is not None:
                    self._unchecked_color = color

        handle_data = theme_map(data.get('handle'))
        if handle_data is not None:
            self._handle_border_rule, self._handle_radius = self._part_frame_rules(handle_data)
            checked_data = theme_map(handle_data.get('checked')) or {}
            unchecked_data = theme_map(handle_data.get('unchecked')) or {}
            handle_background = theme_map(handle_data.get('background')) or {}
            checked_background = theme_map(checked_data.get('background')) or {}
            unchecked_background = theme_map(unchecked_data.get('background')) or {}
            handle_color = handle_data.get('color')
            if isinstance(handle_color, str):
                color = to_qcolor(handle_color)
                if color is not None:
                    self._handle_color = color
                    self._animated_handle_color = None
            handle_bg_color = handle_background.get('color')
            if isinstance(handle_bg_color, str):
                color = to_qcolor(handle_bg_color)
                if color is not None:
                    self._handle_color = color
                    self._animated_handle_color = None
            self._checked_handle_color = None
            for raw in (checked_background.get('color'), checked_data.get('color')):
                if not isinstance(raw, str):
                    continue
                color = to_qcolor(raw)
                if color is not None:
                    self._checked_handle_color = color
                    break
            self._unchecked_handle_color = None
            for raw in (unchecked_background.get('color'), unchecked_data.get('color')):
                if not isinstance(raw, str):
                    continue
                color = to_qcolor(raw)
                if color is not None:
                    self._unchecked_handle_color = color
                    break

        size_data = theme_map(data.get('size')) or {}
        width = coerce_positive_int(size_data.get('width', size_data.get('w')))
        height = coerce_positive_int(size_data.get('height', size_data.get('h')))
        if width is not None and height is not None:
            self._theme_fixed_size = (width, height)
            self.setFixedSize(*self._theme_fixed_size)
        else:
            self._theme_fixed_size = None
            self.setFixedSize(*self._default_size)

        layout_data = theme_map(data.get('layout')) or {}
        margin = layout_data.get('margin')
        if isinstance(margin, int) and margin >= 0:
            limit = max(0, (min(self.width(), self.height()) // 2) - 1)
            self._margin = min(margin, limit)

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

    def has_visible_parts_theme(self) -> bool:
        for color in (
            self._handle_color,
            self._checked_handle_color,
            self._unchecked_handle_color,
            self._checked_color,
            self._unchecked_color,
        ):
            if self._has_visible_color(color):
                return True
        return bool(self._track_border_rule) or bool(self._handle_border_rule)

    def _has_visible_color(self, color: QColor | None) -> bool:
        return isinstance(color, QColor) and color.isValid() and color.alpha() > 0

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

    def _part_frame_rules(self, data: WidgetThemeMap) -> tuple[str, str]:
        border = theme_map(data.get('border')) or {}
        radius = str(border.get('radius', data.get('radius', '0px'))).strip() or '0px'

        width = str(border.get('width', '')).strip()
        style = str(border.get('style', '')).strip()
        color = str(border.get('color', '')).strip()
        border_rule = f'border: {width} {style} {color};' if all((width, style, color)) else ''
        return border_rule, radius

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
