from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPainterPath, QPen, QResizeEvent
from PySide6.QtWidgets import QCheckBox, QSizePolicy, QWidget

from src.theme.colors import to_qcolor
from src.theme.gradients import (
    adjust_gradient_data,
    adjust_qcolor,
    build_background_brush,
    clone_gradient_data,
    normalize_gradient_data,
)
from src.theme.rainbow.palette import sample_rainbow_color
from src.theme.schema.access import coerce_positive_int, theme_map
from src.ui.painting import new_widget_painter
from src.ui.widgets.main.containers import MTWidget
from src.ui.widgets.types import WidgetThemeMap


@dataclass(slots=True)
class _SwitchAppearanceState:
    checked_background_brightness: float = 1.0
    checked_background_saturation: float = 1.0
    unchecked_background_brightness: float = 1.0
    unchecked_background_saturation: float = 1.0
    handle_background_brightness: float = 1.0
    handle_background_saturation: float = 1.0
    checked_handle_background_brightness: float | None = None
    checked_handle_background_saturation: float | None = None
    unchecked_handle_background_brightness: float | None = None
    unchecked_handle_background_saturation: float | None = None


@dataclass(slots=True)
class _SwitchRainbowState:
    palette: str = 'Classic'
    saturation: float = 1.0
    handle_phase: float = 0.0


class MTSwitch(QCheckBox):
    def __init__(
        self,
        text: str = '',
        parent: QWidget | None = None,
        checked: bool = False,
        checked_color: str | None = None,
        unchecked_color: str | None = None,
        handle_color: str | None = None,
        obj_name: str = '',
    ) -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self._checked_background_gradient: WidgetThemeMap | None = None
        self._unchecked_background_gradient: WidgetThemeMap | None = None
        self._handle_background_gradient: WidgetThemeMap | None = None
        self._checked_handle_background_gradient: WidgetThemeMap | None = None
        self._unchecked_handle_background_gradient: WidgetThemeMap | None = None
        self._default_margin = self._margin
        self._default_checked_color = QColor(self._checked_color)
        self._default_unchecked_color = QColor(self._unchecked_color)
        self._default_handle_color = QColor(self._handle_color)
        self._default_checked_background_gradient = None
        self._default_unchecked_background_gradient = None
        self._default_handle_background_gradient = None
        self._track_border_rule = ''
        self._handle_border_rule = ''
        self._track_radius = '0px'
        self._handle_radius = '0px'
        self._default_size = (40, 20)
        self._theme_fixed_size: tuple[int, int] | None = None
        self._appearance = _SwitchAppearanceState()
        self._rainbow = _SwitchRainbowState()
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
        self._sync_visuals(animate=False)

    def sync_size(self, *, bounds_width: int | None = None, bounds_height: int | None = None) -> None:
        target_size = self._theme_fixed_size or self._default_size
        self.setFixedSize(*target_size)
        self._sync_visuals(animate=False)

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
        self._checked_background_gradient = clone_gradient_data(self._default_checked_background_gradient)
        self._unchecked_background_gradient = clone_gradient_data(self._default_unchecked_background_gradient)
        self._handle_background_gradient = clone_gradient_data(self._default_handle_background_gradient)
        self._checked_handle_background_gradient = None
        self._unchecked_handle_background_gradient = None
        self._appearance = _SwitchAppearanceState()
        self._rainbow = _SwitchRainbowState()
        self._animated_handle_color = None
        self._track_border_rule = ''
        self._handle_border_rule = ''
        self._track_radius = '0px'
        self._handle_radius = '0px'
        self._theme_fixed_size = None
        self.setFixedSize(*self._default_size)
        self._sync_visuals(animate=False)

    def _set_color(self, attr_name: str, color_value: str) -> None:
        color = to_qcolor(color_value)
        if color is not None:
            setattr(self, attr_name, color)

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
                self._set_color('_checked_color', checked_color)
            checked_bg_color = checked_background.get('color')
            if isinstance(checked_bg_color, str):
                self._set_color('_checked_color', checked_bg_color)
            unchecked_color = unchecked_data.get('color')
            if isinstance(unchecked_color, str):
                self._set_color('_unchecked_color', unchecked_color)
            unchecked_bg_color = unchecked_background.get('color')
            if isinstance(unchecked_bg_color, str):
                self._set_color('_unchecked_color', unchecked_bg_color)
            if 'gradient' in checked_background:
                self._checked_background_gradient = theme_map(normalize_gradient_data(checked_background.get('gradient')))
            if 'gradient' in unchecked_background:
                self._unchecked_background_gradient = theme_map(normalize_gradient_data(unchecked_background.get('gradient')))
            brightness = checked_background.get('brightness')
            if isinstance(brightness, (int, float)):
                self._appearance.checked_background_brightness = max(0.0, min(float(brightness), 1.0))
            saturation = checked_background.get('saturation')
            if isinstance(saturation, (int, float)):
                self._appearance.checked_background_saturation = max(0.0, min(float(saturation), 1.0))
            brightness = unchecked_background.get('brightness')
            if isinstance(brightness, (int, float)):
                self._appearance.unchecked_background_brightness = max(0.0, min(float(brightness), 1.0))
            saturation = unchecked_background.get('saturation')
            if isinstance(saturation, (int, float)):
                self._appearance.unchecked_background_saturation = max(0.0, min(float(saturation), 1.0))

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
                self._set_color('_handle_color', handle_color)
            handle_bg_color = handle_background.get('color')
            if isinstance(handle_bg_color, str):
                self._set_color('_handle_color', handle_bg_color)
            self._checked_handle_color = self._state_color(checked_data, checked_background)
            self._unchecked_handle_color = self._state_color(unchecked_data, unchecked_background)
            if 'gradient' in handle_background:
                self._handle_background_gradient = theme_map(normalize_gradient_data(handle_background.get('gradient')))
            if 'gradient' in checked_background:
                self._checked_handle_background_gradient = theme_map(normalize_gradient_data(checked_background.get('gradient')))
            if 'gradient' in unchecked_background:
                self._unchecked_handle_background_gradient = theme_map(normalize_gradient_data(unchecked_background.get('gradient')))
            brightness = handle_background.get('brightness')
            if isinstance(brightness, (int, float)):
                self._appearance.handle_background_brightness = max(0.0, min(float(brightness), 1.0))
            saturation = handle_background.get('saturation')
            if isinstance(saturation, (int, float)):
                self._appearance.handle_background_saturation = max(0.0, min(float(saturation), 1.0))
            self._apply_handle_state_adjustments(checked_background, checked=True)
            self._apply_handle_state_adjustments(unchecked_background, checked=False)

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

        self._sync_visuals(animate=False)

    def _state_color(self, state_data: WidgetThemeMap, background_data: WidgetThemeMap) -> QColor | None:
        for raw in (background_data.get('color'), state_data.get('color')):
            if isinstance(raw, str):
                color = to_qcolor(raw)
                if color is not None:
                    return color
        return None

    def _apply_handle_state_adjustments(self, background_data: WidgetThemeMap, *, checked: bool) -> None:
        brightness_attr = (
            'checked_handle_background_brightness'
            if checked else
            'unchecked_handle_background_brightness'
        )
        saturation_attr = (
            'checked_handle_background_saturation'
            if checked else
            'unchecked_handle_background_saturation'
        )
        brightness = background_data.get('brightness')
        if isinstance(brightness, (int, float)):
            setattr(self._appearance, brightness_attr, max(0.0, min(float(brightness), 1.0)))
        saturation = background_data.get('saturation')
        if isinstance(saturation, (int, float)):
            setattr(self._appearance, saturation_attr, max(0.0, min(float(saturation), 1.0)))

    def setChecked(self, checked: bool) -> None:
        previous = self.isChecked()
        super().setChecked(bool(checked))
        current = self.isChecked()
        if previous != current:
            if self.signalsBlocked():
                self._sync_visuals(animate=False)
            return
        return

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_visuals(animate=False)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if not hasattr(self, '_track') or not hasattr(self, '_handle'):
            return
        if self._syncing_visuals:
            return
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.EnabledChange,
        ):
            self._sync_visuals(animate=False, sync_state_props=False)

    def _on_toggled(self, _: bool) -> None:
        self._sync_checked_properties()
        self._queue_visual_state_sync(self.isChecked())

    def _sync_visuals(self, *, animate: bool, sync_state_props: bool = True) -> None:
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

    def _apply_fallback_colors(self) -> None:
        self.update()

    def current_part_color(self, part: str) -> QColor | None:
        key = str(part).strip()
        if key == 'handle':
            if isinstance(self._animated_handle_color, QColor) and self._animated_handle_color.isValid():
                return QColor(self._animated_handle_color)
            checked = self._visual_checked()
            state_color = self._checked_handle_color if checked else self._unchecked_handle_color
            color = state_color if isinstance(state_color, QColor) and state_color.isValid() else self._handle_color
            brightness = (
                self._appearance.checked_handle_background_brightness
                if checked else
                self._appearance.unchecked_handle_background_brightness
            )
            saturation = (
                self._appearance.checked_handle_background_saturation
                if checked else
                self._appearance.unchecked_handle_background_saturation
            )
            return adjust_qcolor(
                color,
                brightness=self._appearance.handle_background_brightness if brightness is None else brightness,
                saturation=self._appearance.handle_background_saturation if saturation is None else saturation,
            )
        if key == 'track':
            checked = self._visual_checked()
            color = self._checked_color if checked else self._unchecked_color
            brightness = self._appearance.checked_background_brightness if checked else self._appearance.unchecked_background_brightness
            saturation = self._appearance.checked_background_saturation if checked else self._appearance.unchecked_background_saturation
            return adjust_qcolor(color, brightness=brightness, saturation=saturation)
        return None

    def current_part_gradient(self, part: str) -> WidgetThemeMap | None:
        key = str(part).strip()
        if key == 'handle':
            checked = self._visual_checked()
            gradient = (
                self._checked_handle_background_gradient
                if checked else
                self._unchecked_handle_background_gradient
            )
            if gradient is None:
                gradient = self._handle_background_gradient
            brightness = (
                self._appearance.checked_handle_background_brightness
                if checked else
                self._appearance.unchecked_handle_background_brightness
            )
            saturation = (
                self._appearance.checked_handle_background_saturation
                if checked else
                self._appearance.unchecked_handle_background_saturation
            )
            return adjust_gradient_data(
                gradient,
                brightness=self._appearance.handle_background_brightness if brightness is None else brightness,
                saturation=self._appearance.handle_background_saturation if saturation is None else saturation,
            )
        if key == 'track':
            checked = self._visual_checked()
            gradient = self._checked_background_gradient if checked else self._unchecked_background_gradient
            brightness = self._appearance.checked_background_brightness if checked else self._appearance.unchecked_background_brightness
            saturation = self._appearance.checked_background_saturation if checked else self._appearance.unchecked_background_saturation
            return adjust_gradient_data(gradient, brightness=brightness, saturation=saturation)
        return None

    def set_part_color(self, part: str, value: object) -> bool:
        color = to_qcolor(value)
        if color is None:
            return False

        key = str(part).strip()
        if key == 'handle':
            self._handle_color = QColor(color)
            self._checked_handle_color = None
            self._unchecked_handle_color = None
            self._handle_background_gradient = None
            self._checked_handle_background_gradient = None
            self._unchecked_handle_background_gradient = None
            self._animated_handle_color = None
        elif key == 'track':
            self._checked_color = QColor(color)
            self._unchecked_color = QColor(color)
            self._checked_background_gradient = None
            self._unchecked_background_gradient = None
        else:
            return False

        self._apply_fallback_colors()
        return True

    def set_part_gradient(self, part: str, value: object) -> bool:
        gradient = theme_map(normalize_gradient_data(value))
        if gradient is None:
            return False

        key = str(part).strip()
        if key == 'handle':
            self._handle_background_gradient = gradient
            self._checked_handle_background_gradient = None
            self._unchecked_handle_background_gradient = None
            self._animated_handle_color = None
        elif key == 'track':
            self._checked_background_gradient = clone_gradient_data(gradient)
            self._unchecked_background_gradient = clone_gradient_data(gradient)
        else:
            return False

        self._apply_fallback_colors()
        return True

    def set_part_style_value(self, part: str, path: tuple[str, ...], value: object) -> bool:
        if path in {('color',), ('background', 'color')}:
            return self.set_part_color(part, value)
        if path == ('background', 'gradient'):
            return self.set_part_gradient(part, value)
        return False

    def set_handle_rainbow(self, value: float) -> None:
        try:
            phase = float(value) % 1.0
        except (TypeError, ValueError):
            phase = 0.0
        self._rainbow.handle_phase = phase
        self._animated_handle_color = self._sample_rainbow_color(phase)
        self.update()

    def clear_handle_rainbow(self) -> None:
        self._rainbow.handle_phase = 0.0
        self._animated_handle_color = None
        self._apply_fallback_colors()
        self.update()

    def set_handle_rainbow_saturation(self, value: float) -> None:
        try:
            self._rainbow.saturation = max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            self._rainbow.saturation = 1.0
        if self._rainbow.handle_phase:
            self.set_handle_rainbow(self._rainbow.handle_phase)

    def set_handle_rainbow_palette(self, value: str) -> None:
        self._rainbow.palette = str(value or 'Pastel').strip() or 'Pastel'
        if self._rainbow.handle_phase:
            self.set_handle_rainbow(self._rainbow.handle_phase)

    def _sample_rainbow_color(self, phase: float) -> QColor:
        return sample_rainbow_color(
            phase,
            palette=self._rainbow.palette,
            brightness=self._appearance.handle_background_brightness,
            saturation=self._appearance.handle_background_saturation * self._rainbow.saturation,
        )

    def current_handle_rainbow(self) -> float:
        return float(self._rainbow.handle_phase)

    def has_visible_parts_theme(self) -> bool:
        return (
            self._has_visible_color(self._checked_color)
            or self._has_visible_color(self._unchecked_color)
            or self._has_visible_color(self._handle_color)
            or self._has_visible_color(self._checked_handle_color)
            or self._has_visible_color(self._unchecked_handle_color)
            or isinstance(self._checked_background_gradient, dict)
            or isinstance(self._unchecked_background_gradient, dict)
            or isinstance(self._handle_background_gradient, dict)
            or isinstance(self._checked_handle_background_gradient, dict)
            or isinstance(self._unchecked_handle_background_gradient, dict)
            or bool(self._track_border_rule)
            or bool(self._handle_border_rule)
        )

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

        painter.save()
        painter.setBrush(self._part_brush(part, rect))

        border_rule = self._track_border_rule if part == 'track' else self._handle_border_rule
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

        radius_value = self._track_radius if part == 'track' else self._handle_radius
        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        painter.drawPath(self._rounded_path(draw_rect, self._resolve_radius_float(draw_rect, radius_value)))
        painter.restore()

    def _part_brush(self, part: str, rect: QRectF) -> QColor | Qt.BrushStyle | object:
        gradient = self.current_part_gradient(part)
        if gradient is not None:
            brush = build_background_brush(rect, {'gradient': gradient})
            if brush is not None:
                return brush

        color = self.current_part_color(part)
        if isinstance(color, QColor) and color.isValid():
            return color
        return Qt.BrushStyle.NoBrush

    def _parse_border_rule(self, rule: str) -> tuple[float, Qt.PenStyle, QColor]:
        text = str(rule or '').strip()
        if not text.startswith('border:'):
            return 0.0, Qt.PenStyle.NoPen, QColor()

        value = text.removeprefix('border:').strip().rstrip(';').strip()
        parts = [part for part in value.split() if part]
        if len(parts) < 3:
            return 0.0, Qt.PenStyle.NoPen, QColor()

        width = self._parse_float_px(parts[0])
        style = self._pen_style(parts[1])
        color = to_qcolor(' '.join(parts[2:]))
        return width, style, color if color is not None else QColor()

    def _parse_float_px(self, value: object) -> float:
        if isinstance(value, (int, float)):
            return max(0.0, float(value))
        text = str(value or '').strip().lower()
        if text.endswith('px'):
            text = text[:-2].strip()
        try:
            return max(0.0, float(text))
        except ValueError:
            return 0.0

    def _pen_style(self, value: object) -> Qt.PenStyle:
        text = str(value).strip().lower()
        match text:
            case 'none':
                return Qt.PenStyle.NoPen
            case 'dash' | 'dashed':
                return Qt.PenStyle.DashLine
            case 'dot' | 'dotted':
                return Qt.PenStyle.DotLine
            case 'dashdot':
                return Qt.PenStyle.DashDotLine
            case 'dashdotdot':
                return Qt.PenStyle.DashDotDotLine
            case _:
                return Qt.PenStyle.SolidLine

    def _resolve_radius_float(self, rect: QRectF, value: str) -> float:
        text = str(value or '').strip().lower()
        max_radius = max(0.0, min(rect.width(), rect.height()) / 2.0)
        if not text:
            return 0.0
        if text.endswith('%'):
            try:
                return max(0.0, min(max_radius, (min(rect.width(), rect.height()) * float(text[:-1].strip())) / 100.0))
            except ValueError:
                return 0.0
        if text.endswith('px'):
            text = text[:-2].strip()
        try:
            return max(0.0, min(max_radius, float(text)))
        except ValueError:
            return 0.0

    def _rounded_path(self, rect: QRectF, radius: float) -> QPainterPath:
        path = QPainterPath()
        if rect.isValid() and rect.width() > 0 and rect.height() > 0:
            path.addRoundedRect(rect, radius, radius)
        return path

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

        self._checked_state_cache = checked
        checked_value = 'true' if checked else 'false'
        for widget in (self, self._track, self._handle):
            widget.setProperty('checked', checked_value)
            if widget.property('unchecked') is not None:
                widget.setProperty('unchecked', None)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
