from copy import deepcopy
from math import ceil
from time import monotonic
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimerEvent
from PySide6.QtGui import (
    QBrush,
    QColor,
    QEnterEvent,
    QFocusEvent,
    QPalette,
    QLinearGradient,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QLineEdit,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QStyleOptionSpinBox,
    QStyleOptionSlider,
    QWidget,
)

from src.theme.colors import to_qcolor
from src.theme.gradients import (
    adjust_gradient_data,
    adjust_qcolor,
    build_background_brush,
    normalize_gradient_data,
)
from src.theme.schema.access import coerce_box_sides, coerce_number, theme_map
from src.translation.manager import translator as t
from src.theme.rainbow.palette import sample_rainbow_color
from src.ui.painting import configure_painter, draw_widget_background, new_widget_painter
from src.ui.widgets.custom.box import BoxThemeMixin
from src.ui.widgets.custom.text import TextEffectMixin
from src.ui.widgets.custom.types import WidgetThemeMap


def _text_render_width(widget: QWidget, values: tuple[str, ...]) -> int:
    metrics = widget.fontMetrics()
    widths = [metrics.horizontalAdvance(str(value)) for value in values if str(value)]
    return max(widths or [1])


def _line_edit_horizontal_margins(line_edit: QLineEdit) -> int:
    margins = line_edit.textMargins()
    return max(0, margins.left() + margins.right())


def _spin_box_text_safety_width(spin_box: QSpinBox | QDoubleSpinBox) -> int:
    metrics = spin_box.fontMetrics()
    return max(4, metrics.horizontalAdvance('0'))


def _spin_box_content_size_hint(spin_box: QSpinBox | QDoubleSpinBox, values: tuple[str, ...]) -> QSize:
    text_width = (
        _text_render_width(spin_box, values) +
        _line_edit_horizontal_margins(spin_box.lineEdit()) +
        _spin_box_text_safety_width(spin_box)
    )
    content_size = QSize(max(1, text_width), max(1, spin_box.fontMetrics().height()))

    option = QStyleOptionSpinBox()
    spin_box.initStyleOption(option)
    option.buttonSymbols = QSpinBox.ButtonSymbols.NoButtons
    option.frame = False

    return spin_box.style().sizeFromContents(
        QStyle.ContentsType.CT_SpinBox,
        option,
        content_size,
        spin_box,
    )


class MTSlider(QSlider):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self._dragging_anywhere = False
        self._drag_offset = 0
        self._slider_line_rainbow_phase = 0.0
        self._runtime_rainbow_palette = 'Pastel'
        self._runtime_rainbow_saturation = 1.0
        self._rainbow_line_color: QColor | None = None
        self._default_parts = self._build_default_parts()
        self._parts = deepcopy(self._default_parts)
        self.valueChanged.connect(self.update)
        def _update_range(_: int, __: int) -> None:
            self.update()

        self.rangeChanged.connect(_update_range)
        self.sliderPressed.connect(self.update)
        self.sliderReleased.connect(self.update)

        if obj_name:
            self.setObjectName(obj_name)

    def sizeHint(self) -> QSize:
        return self._expanded_slider_size(super().sizeHint())

    def minimumSizeHint(self) -> QSize:
        return self._expanded_slider_size(super().minimumSizeHint())

    def _build_default_parts(self) -> dict[str, dict[str, object]]:
        transparent = QColor(Qt.GlobalColor.transparent)
        return {
            'groove': {
                'background_color': QColor(transparent),
                'background_gradient': None,
                'border_color': QColor(transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'size': 6.0,
                'brightness': 1.0,
                'saturation': 1.0,
            },
            'sub_page': {
                'background_color': QColor(transparent),
                'background_gradient': None,
                'border_color': QColor(transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'brightness': 1.0,
                'saturation': 1.0,
            },
            'add_page': {
                'background_color': QColor(transparent),
                'background_gradient': None,
                'border_color': QColor(transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'brightness': 1.0,
                'saturation': 1.0,
            },
            'handle': {
                'background_color': QColor(transparent),
                'background_gradient': None,
                'border_color': QColor(transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'width': 14.0,
                'height': 14.0,
                'margin': (-4.0, 0.0, -4.0, 0.0),
                'brightness': 1.0,
                'saturation': 1.0,
            },
        }

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_anywhere = True
            self.setSliderDown(True)
            self.grabMouse()
            handle = self._handle_rect(self._create_option_slider())
            point = event.position().toPoint()
            if handle.contains(point):
                self._drag_offset = self._extract_drag_offset(point, handle)
            else:
                self._jump_to_cursor(event.position())
                new_handle = self._handle_rect(self._create_option_slider())
                if self.orientation() == Qt.Orientation.Horizontal:
                    self._drag_offset = max(0, new_handle.width() // 2)
                else:
                    self._drag_offset = max(0, new_handle.height() // 2)
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_anywhere and (event.buttons() & Qt.MouseButton.LeftButton):
            self._drag_with_offset(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_anywhere:
            self._drag_with_offset(event.position())
            self._dragging_anywhere = False
            if QWidget.mouseGrabber() is self:
                self.releaseMouse()
            self.setSliderDown(False)
            event.accept()
            return
        event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

    def _jump_to_cursor(self, pos: QPointF) -> None:
        handle = self._handle_rect(self._create_option_slider())
        if self.orientation() == Qt.Orientation.Horizontal:
            self._set_value_from_cursor(pos, handle.width() // 2)
        else:
            self._set_value_from_cursor(pos, handle.height() // 2)

    def _drag_with_offset(self, pos: QPointF) -> None:
        self._set_value_from_cursor(pos, self._drag_offset)

    def _set_value_from_cursor(self, pos: QPointF, offset: int) -> None:
        option = self._create_option_slider()
        handle = self._handle_rect(option)
        groove = QRectF(self._groove_rect(option))

        if self.orientation() == Qt.Orientation.Horizontal:
            span = max(0, int(round(groove.width())))
            handle_left = float(pos.x()) - float(offset)
            center_position = handle_left + (handle.width() / 2.0) - groove.left()
        else:
            span = max(0, int(round(groove.height())))
            handle_top = float(pos.y()) - float(offset)
            center_position = handle_top + (handle.height() / 2.0) - groove.top()

        position = max(0, min(span, int(round(center_position))))
        value = QStyle.sliderValueFromPosition(
            self.minimum(),
            self.maximum(),
            position,
            span,
            option.upsideDown
        )
        self.setValue(value)

    def _extract_drag_offset(self, point: QPoint, handle: QRect) -> int:
        if self.orientation() == Qt.Orientation.Horizontal:
            offset = point.x() - handle.x()
            return max(0, min(handle.width(), offset))

        offset = point.y() - handle.y()
        return max(0, min(handle.height(), offset))

    def _create_option_slider(self) -> QStyleOptionSlider:
        option = QStyleOptionSlider()
        option.initFrom(self)
        option.orientation = self.orientation()
        option.minimum = self.minimum()
        option.maximum = self.maximum()
        option.sliderPosition = self.value()
        option.sliderValue = self.value()
        option.upsideDown = bool(self.invertedAppearance())
        return option

    def _part_value(self, part: str, key: str, fallback: object = None) -> object:
        return self._parts.get(part, {}).get(key, fallback)

    def _resolve_radius(self, value: object, rect: QRectF) -> float:
        base = max(0.0, min(rect.width(), rect.height()) / 2.0)
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), base))
        if isinstance(value, str):
            text = value.strip().lower()
            if text.endswith('%'):
                try:
                    percent = float(text[:-1].strip())
                except ValueError:
                    return base
                return max(0.0, min((min(rect.width(), rect.height()) * percent) / 100.0, base))
            if text.endswith('px'):
                text = text[:-2].strip()
            try:
                return max(0.0, min(float(text), base))
            except ValueError:
                return base
        return base

    def _resolve_length(self, value: object, *, base: float, fallback: float) -> float:
        if isinstance(value, (int, float)):
            return max(0.0, float(value))
        if isinstance(value, str):
            text = value.strip().lower()
            if text.endswith('%'):
                try:
                    return max(0.0, (base * float(text[:-1].strip())) / 100.0)
                except ValueError:
                    return fallback
            if text.endswith('px'):
                text = text[:-2].strip()
            try:
                return max(0.0, float(text))
            except ValueError:
                return fallback
        return fallback

    def _current_handle_color(self) -> QColor:
        animated = getattr(self, '_animated_handle_color', None)
        if isinstance(animated, QColor) and animated.isValid():
            return QColor(animated)
        color = self._part_value('handle', 'background_color')
        base = QColor(color) if isinstance(color, QColor) and color.isValid() else QColor(Qt.GlobalColor.transparent)
        return self._adjust_part_color('handle', base)

    def _part_brightness(self, part: str) -> float:
        value = self._part_value(part, 'brightness', 1.0)
        return max(0.0, min(float(value), 1.0)) if isinstance(value, (int, float)) else 1.0

    def _part_saturation(self, part: str) -> float:
        value = self._part_value(part, 'saturation', 1.0)
        return max(0.0, min(float(value), 1.0)) if isinstance(value, (int, float)) else 1.0

    def _adjust_part_color(self, part: str, color: QColor) -> QColor:
        return adjust_qcolor(color, brightness=self._part_brightness(part), saturation=self._part_saturation(part))

    def _adjust_part_gradient(self, part: str, gradient: WidgetThemeMap | None) -> WidgetThemeMap | None:
        return adjust_gradient_data(gradient, brightness=self._part_brightness(part), saturation=self._part_saturation(part))

    def current_part_color(self, part: str) -> QColor:
        if part == 'handle':
            return self._current_handle_color()
        if part == 'sub_page' and isinstance(self._rainbow_line_color, QColor) and self._rainbow_line_color.isValid():
            return self._adjust_part_color(part, QColor(self._rainbow_line_color))
        color = self._part_value(part, 'background_color')
        if isinstance(color, QColor) and color.isValid():
            return self._adjust_part_color(part, color)
        return QColor()

    def current_part_gradient(self, part: str) -> WidgetThemeMap | None:
        animated = getattr(self, '_animated_handle_color', None)
        if part == 'handle' and isinstance(animated, QColor) and animated.isValid():
            return None
        if part == 'sub_page' and isinstance(self._rainbow_line_color, QColor) and self._rainbow_line_color.isValid():
            return None
        return self._adjust_part_gradient(part, theme_map(self._part_value(part, 'background_gradient')))

    def set_part_color(self, part: str, value: object) -> bool:
        color = to_qcolor(value)
        if color is None or part not in self._parts:
            return False
        self._parts[part]['background_color'] = QColor(color)
        self._parts[part]['background_gradient'] = None
        if part == 'handle':
            self._animated_handle_color = QColor(color)
        self.update()
        return True

    def set_part_gradient(self, part: str, value: object) -> bool:
        gradient = theme_map(normalize_gradient_data(value))
        if gradient is None or part not in self._parts:
            return False
        self._parts[part]['background_gradient'] = gradient
        self.update()
        return True

    def set_part_style_value(self, part: str, path: tuple[str, ...], value: object) -> bool:
        if part not in self._parts:
            return False
        if path in {('color',), ('background', 'color')}:
            return self.set_part_color(part, value)
        if path == ('background', 'gradient'):
            return self.set_part_gradient(part, value)
        if path == ('border', 'color'):
            color = to_qcolor(value)
            if color is None:
                return False
            self._parts[part]['border_color'] = QColor(color)
            self.update()
            return True
        if path == ('border', 'width'):
            number = coerce_number(value)
            if number is None:
                return False
            self._parts[part]['border_width'] = max(0.0, float(number))
            self.update()
            return True
        if path == ('border', 'radius'):
            self._parts[part]['border_radius'] = value
            self.update()
            return True
        return False

    def set_part_metric(self, part: str, metric: str, value: float) -> bool:
        if part not in self._parts:
            return False
        if part == 'groove' and metric == 'size':
            self._parts[part]['size'] = max(0.0, float(value))
        elif part == 'handle' and metric in {'width', 'height'}:
            self._parts[part][metric] = max(0.0, float(value))
        else:
            return False
        self.update()
        return True

    def _handle_size(self) -> tuple[float, float]:
        rect = self.contentsRect()
        width = self._resolve_length(self._part_value('handle', 'width'), base=rect.width(), fallback=14.0)
        height = self._resolve_length(self._part_value('handle', 'height'), base=rect.height(), fallback=14.0)
        return max(1.0, width), max(1.0, height)

    def _handle_margin(self) -> tuple[float, float, float, float]:
        margin = coerce_box_sides(self._part_value('handle', 'margin'), allow_negative=True)
        return margin if margin is not None else (0.0, 0.0, 0.0, 0.0)

    def _groove_thickness(self) -> float:
        rect = self.contentsRect()
        base = rect.height() if self.orientation() == Qt.Orientation.Horizontal else rect.width()
        return max(1.0, self._resolve_length(self._part_value('groove', 'size'), base=base, fallback=6.0))

    def _expanded_slider_size(self, hint: QSize) -> QSize:
        handle_w, handle_h = self._handle_size()
        top, right, bottom, left = self._handle_margin()
        extra_w = int(round(max(0.0, left) + max(0.0, right)))
        extra_h = int(round(max(0.0, top) + max(0.0, bottom)))
        if self.orientation() == Qt.Orientation.Horizontal:
            min_height = int(round(max(handle_h, self._groove_thickness()) + extra_h))
            min_width = int(round(handle_w + extra_w))
            return QSize(max(1, min_width), max(1, min_height))
        min_width = int(round(max(handle_w, self._groove_thickness()) + extra_w))
        min_height = int(round(handle_h + extra_h))
        return QSize(max(1, min_width), max(1, min_height))

    def _handle_rect(self, option: QStyleOptionSlider | None = None) -> QRect:
        rect = QRectF(self.contentsRect())
        groove = QRectF(self._groove_rect(option))
        handle_w, handle_h = self._handle_size()
        top, right, bottom, left = self._handle_margin()
        upside_down = bool(option.upsideDown) if option is not None else bool(self.invertedAppearance())
        if self.orientation() == Qt.Orientation.Horizontal:
            span = max(0, int(round(groove.width())))
            position = QStyle.sliderPositionFromValue(
                self.minimum(),
                self.maximum(),
                self.value(),
                span,
                upside_down,
            )
            center_x = groove.left() + float(position)
            x = center_x - (handle_w / 2.0)
            y = rect.center().y() - (handle_h / 2.0) + ((top - bottom) / 2.0)
        else:
            span = max(0, int(round(groove.height())))
            position = QStyle.sliderPositionFromValue(
                self.minimum(),
                self.maximum(),
                self.value(),
                span,
                upside_down,
            )
            x = rect.center().x() - (handle_w / 2.0) + ((left - right) / 2.0)
            center_y = groove.top() + float(position)
            y = center_y - (handle_h / 2.0)
        return QRect(int(round(x)), int(round(y)), int(round(handle_w)), int(round(handle_h)))

    def _groove_rect(self, option: QStyleOptionSlider | None = None) -> QRect:
        rect = QRectF(self.contentsRect())
        thickness = self._groove_thickness()
        handle_w, handle_h = self._handle_size()
        if self.orientation() == Qt.Orientation.Horizontal:
            x = rect.x() + (handle_w / 2.0)
            width = max(0.0, rect.width() - handle_w)
            y = rect.center().y() - (thickness / 2.0)
            return QRect(int(round(x)), int(round(y)), int(round(width)), int(round(thickness)))
        x = rect.center().x() - (thickness / 2.0)
        y = rect.y() + (handle_h / 2.0)
        height = max(0.0, rect.height() - handle_h)
        return QRect(int(round(x)), int(round(y)), int(round(thickness)), int(round(height)))

    def set_slider_line_rainbow(self, value: float) -> QColor:
        try:
            phase = float(value) % 1.0
        except (TypeError, ValueError):
            phase = 0.0
        self._slider_line_rainbow_phase = phase
        color = self._sample_rainbow_color(phase)
        self._rainbow_line_color = QColor(color)
        self.update()
        return color

    def clear_slider_line_rainbow(self) -> None:
        self._slider_line_rainbow_phase = 0.0
        self._rainbow_line_color = None
        self.update()

    def set_slider_line_rainbow_saturation(self, value: float) -> None:
        try:
            self._runtime_rainbow_saturation = max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            self._runtime_rainbow_saturation = 1.0
        if isinstance(self._rainbow_line_color, QColor):
            self._rainbow_line_color = self._sample_rainbow_color(self._slider_line_rainbow_phase)
            self.update()

    def set_slider_line_rainbow_palette(self, value: str) -> None:
        self._runtime_rainbow_palette = str(value or 'Pastel').strip() or 'Pastel'
        if isinstance(self._rainbow_line_color, QColor):
            self._rainbow_line_color = self._sample_rainbow_color(self._slider_line_rainbow_phase)
            self.update()

    def current_slider_line_rainbow(self) -> float:
        return float(self._slider_line_rainbow_phase)

    def reset_theme(self) -> None:
        self._slider_line_rainbow_phase = 0.0
        self._runtime_rainbow_palette = 'Pastel'
        self._runtime_rainbow_saturation = 1.0
        self._parts = deepcopy(self._default_parts)
        self._rainbow_line_color = None
        self._animated_handle_color = None
        self.update()

    def apply_theme(self, data: WidgetThemeMap) -> None:
        for part in ('groove', 'sub_page', 'add_page', 'handle'):
            part_data = theme_map(data.get(part))
            if part_data is None:
                continue
            background = theme_map(part_data.get('background')) or {}
            border = theme_map(part_data.get('border')) or {}
            if (color := to_qcolor(background.get('color'))):
                self._parts[part]['background_color'] = color
                self._parts[part]['background_gradient'] = None
                if part == 'handle':
                    self._animated_handle_color = None
            if 'gradient' in background:
                self._parts[part]['background_gradient'] = theme_map(normalize_gradient_data(background.get('gradient')))
            if (border_color := to_qcolor(border.get('color'))):
                self._parts[part]['border_color'] = border_color
            if (border_width := coerce_number(border.get('width'))) is not None:
                self._parts[part]['border_width'] = max(0.0, border_width)
            if isinstance((border_style := border.get('style')), str) and border_style.strip():
                self._parts[part]['border_style'] = border_style.strip().lower()
            if (border_radius := border.get('radius')) is not None:
                self._parts[part]['border_radius'] = border_radius
            brightness = background.get('brightness')
            if isinstance(brightness, (int, float)):
                self._parts[part]['brightness'] = max(0.0, min(float(brightness), 1.0))
            saturation = background.get('saturation')
            if isinstance(saturation, (int, float)):
                self._parts[part]['saturation'] = max(0.0, min(float(saturation), 1.0))
            if part == 'groove' and (size := coerce_number(part_data.get('size'))) is not None:
                self._parts[part]['size'] = max(1.0, size)
            if part == 'handle':
                if (width := coerce_number(part_data.get('width'))) is not None:
                    self._parts[part]['width'] = max(1.0, width)
                if (height := coerce_number(part_data.get('height'))) is not None:
                    self._parts[part]['height'] = max(1.0, height)
                if (margin := coerce_box_sides(part_data.get('margin'), allow_negative=True)) is not None:
                    self._parts[part]['margin'] = margin

        if isinstance(self._rainbow_line_color, QColor):
            self._rainbow_line_color = self._sample_rainbow_color(self._slider_line_rainbow_phase)
        self.update()

    def _sample_rainbow_color(self, phase: float) -> QColor:
        return sample_rainbow_color(
            phase,
            palette=self._runtime_rainbow_palette,
            saturation=self._runtime_rainbow_saturation,
        )

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

    def _rounded_path(self, rect: QRectF, tl: float, tr: float, br: float, bl: float) -> QPainterPath:
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
            return QPainterPath()

        max_rx = rect.width() / 2.0
        max_ry = rect.height() / 2.0
        tl = max(0.0, min(tl, max_rx, max_ry))
        tr = max(0.0, min(tr, max_rx, max_ry))
        br = max(0.0, min(br, max_rx, max_ry))
        bl = max(0.0, min(bl, max_rx, max_ry))

        path = QPainterPath()
        path.moveTo(rect.left() + tl, rect.top())
        
        path.lineTo(rect.right() - tr, rect.top())
        if tr > 0: path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + tr)
        else:      path.lineTo(rect.right(), rect.top())

        path.lineTo(rect.right(), rect.bottom() - br)
        if br > 0: path.quadTo(rect.right(), rect.bottom(), rect.right() - br, rect.bottom())
        else:      path.lineTo(rect.right(), rect.bottom())

        path.lineTo(rect.left() + bl, rect.bottom())
        if bl > 0: path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - bl)
        else:      path.lineTo(rect.left(), rect.bottom())

        path.lineTo(rect.left(), rect.top() + tl)
        if tl > 0: path.quadTo(rect.left(), rect.top(), rect.left() + tl, rect.top())
        else:      path.lineTo(rect.left(), rect.top())
        
        path.closeSubpath()
        return path

    def _part_corner_radii(self, part: str, rect: QRectF) -> tuple[float, float, float, float]:
        radius_value = self._part_value(part, 'border_radius', None)
        if radius_value is None and part in {'sub_page', 'add_page'}:
            radius_value = self._part_value('groove', 'border_radius', None)
        radius = self._resolve_radius(radius_value, rect) if radius_value is not None else 0.0
        if part == 'sub_page':
            if self.orientation() == Qt.Orientation.Horizontal:
                return radius, 0.0, 0.0, radius
            return 0.0, 0.0, radius, radius
        if part == 'add_page':
            if self.orientation() == Qt.Orientation.Horizontal:
                return 0.0, radius, radius, 0.0
            return radius, radius, 0.0, 0.0
        return radius, radius, radius, radius

    def _draw_part_rect(self, painter: QPainter, rect: QRectF, part: str, *, draw_fill: bool = True, draw_border: bool = True) -> None:
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
            return

        painter.save()

        background = self.current_part_color(part)
        background_gradient = self.current_part_gradient(part)
        border_color = self._part_value(part, 'border_color')
        border_width_value = coerce_number(self._part_value(part, 'border_width', 0.0))
        border_width = border_width_value if border_width_value is not None else 0.0
        border_style = self._pen_style(self._part_value(part, 'border_style', 'solid'))

        if draw_fill and background_gradient is not None:
            brush = build_background_brush(rect, {'gradient': background_gradient})
            painter.setBrush(brush if brush is not None else Qt.BrushStyle.NoBrush)
        elif draw_fill and background.isValid():
            painter.setBrush(background)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if not draw_border or border_style == Qt.PenStyle.NoPen or border_width <= 0.0:
            pen = Qt.PenStyle.NoPen
        else:
            color = border_color if isinstance(border_color, QColor) and border_color.isValid() else QColor(Qt.GlobalColor.transparent)
            color = self._adjust_part_color(part, color)
            qpen = QPen(color, border_width)
            qpen.setStyle(border_style)
            qpen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            qpen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen = qpen
        painter.setPen(pen)

        inset = border_width / 2.0 if isinstance(pen, QPen) else 0.0
        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        path = self._rounded_path(draw_rect, *self._part_corner_radii(part, draw_rect))
        painter.drawPath(path)
        painter.restore()

    def paintEvent(self, event: QPaintEvent) -> None:
        _ = event
        painter = new_widget_painter(self, smooth_pixmap=True)

        groove_rect = QRectF(self._groove_rect(self._create_option_slider()))
        handle_rect = QRectF(self._handle_rect(self._create_option_slider()))
        if not groove_rect.isValid() or not handle_rect.isValid():
            painter.end()
            return

        if self.orientation() == Qt.Orientation.Horizontal:
            handle_center = handle_rect.center().x()
            sub_rect = QRectF(groove_rect.left(), groove_rect.top(), max(0.0, handle_center - groove_rect.left()), groove_rect.height())
            add_rect = QRectF(handle_center, groove_rect.top(), max(0.0, groove_rect.right() - handle_center), groove_rect.height())
        else:
            handle_center = handle_rect.center().y()
            sub_rect = QRectF(groove_rect.left(), handle_center, groove_rect.width(), max(0.0, groove_rect.bottom() - handle_center))
            add_rect = QRectF(groove_rect.left(), groove_rect.top(), groove_rect.width(), max(0.0, handle_center - groove_rect.top()))

        self._draw_part_rect(painter, add_rect, 'add_page')
        self._draw_part_rect(painter, sub_rect, 'sub_page')
        self._draw_part_rect(painter, groove_rect, 'groove', draw_fill=False, draw_border=True)
        self._draw_part_rect(painter, handle_rect, 'handle')
        painter.end()

class MTLineEdit(BoxThemeMixin, TextEffectMixin, QLineEdit):
    PAINTED_BOX_THEME = False

    _OVERFLOW_SCROLL_DELAY = 0.55
    _OVERFLOW_SCROLL_EDGE_PAUSE = 0.85
    _OVERFLOW_SCROLL_SPEED = 28.0

    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)
        self._focused_alignment: Qt.AlignmentFlag | None = None
        self._unfocused_alignment: Qt.AlignmentFlag | None = None
        self._theme_text_color_override: QColor | None = None
        self._theme_placeholder_color_override: QColor | None = None
        self._placeholder_tr_key: str | None = None
        self._overflow_hover_active = False
        self._overflow_animation_timer_id = 0
        self._overflow_animation_started_at = 0.0
        self.setFrame(False)
        self.setTextMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)
        t.language_changed.connect(self._update_placeholder_translation)

        if obj_name:
            self.setObjectName(obj_name)

    def sizeHint(self) -> QSize:
        return self._content_size_hint()

    def minimumSizeHint(self) -> QSize:
        hint = self._content_size_hint()
        return QSize(1, hint.height())

    def set_focus_alignments(
        self,
        *,
        focused: Qt.AlignmentFlag | None = None,
        unfocused: Qt.AlignmentFlag | None = None,
    ) -> None:
        self._focused_alignment = focused
        self._unfocused_alignment = unfocused
        self._apply_focus_alignment()

    def clear_focus_alignments(self) -> None:
        self._focused_alignment = None
        self._unfocused_alignment = None

    def set_line_edit_text_theme(
        self,
        *,
        text_color: QColor | None = None,
        placeholder_color: QColor | None = None,
    ) -> None:
        self._theme_text_color_override = QColor(text_color) if isinstance(text_color, QColor) and text_color.isValid() else None
        self._theme_placeholder_color_override = (
            QColor(placeholder_color)
            if isinstance(placeholder_color, QColor) and placeholder_color.isValid()
            else None
        )
        self._apply_theme_palette_overrides()

    def clear_line_edit_text_theme(self) -> None:
        self._theme_text_color_override = None
        self._theme_placeholder_color_override = None
        self._apply_theme_palette_overrides()

    def set_placeholder_tr_key(self, key: str | None) -> None:
        normalized = str(key).strip() if isinstance(key, str) else ''
        self._placeholder_tr_key = normalized or None
        self._update_placeholder_translation()

    def _content_size_hint(self) -> QSize:
        text = self.text() or self.placeholderText()
        width = _text_render_width(self, (text,)) + _line_edit_horizontal_margins(self)
        return QSize(max(1, width), max(1, self.fontMetrics().height()))

    def _update_placeholder_translation(self) -> None:
        if not self._placeholder_tr_key:
            return
        self.setPlaceholderText(t.tr(self._placeholder_tr_key))

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self._set_overflow_hover_active(False)
        self._apply_focus_alignment()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._apply_focus_alignment()
        self._set_overflow_hover_active(self.underMouse())

    def enterEvent(self, event: QEnterEvent) -> None:
        if not self.hasFocus():
            self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event: QTimerEvent) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.hasFocus():
            self._draw_line_edit_background()
            super().paintEvent(event)
            return

        text = self.displayText() or self.placeholderText()
        text_rect = self._visible_text_rect()
        if text and self._text_overflows_rect(text, text_rect):
            painter = new_widget_painter(self, text_antialias=True)
            self._draw_line_edit_background(painter)
            self._draw_faded_text(painter, text_rect, text, self._text_color(text))
            painter.end()
            return

        self._draw_line_edit_background()
        super().paintEvent(event)

    def _apply_focus_alignment(self) -> None:
        alignment = self._focused_alignment if self.hasFocus() else self._unfocused_alignment
        if alignment is not None:
            self.setAlignment(alignment)

    def _apply_theme_palette_overrides(self) -> None:
        palette = QPalette(self.palette())
        if isinstance(self._theme_text_color_override, QColor):
            palette.setColor(QPalette.ColorRole.Text, self._theme_text_color_override)
        if isinstance(self._theme_placeholder_color_override, QColor):
            palette.setColor(QPalette.ColorRole.PlaceholderText, self._theme_placeholder_color_override)
        self.setPalette(palette)
        self.update()

    def _draw_line_edit_background(self, painter: QPainter | None = None) -> None:
        should_end = painter is None
        if painter is None:
            painter = new_widget_painter(self)

        draw_widget_background(self, painter)

        if should_end:
            painter.end()

    def _visible_text_rect(self) -> QRectF:
        margins = self.textMargins()
        return QRectF(self.contentsRect()).adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )

    def _text_overflows_rect(self, text: str, rect: QRectF) -> bool:
        return _text_render_width(self, (text,)) > max(0, int(rect.width()))

    def _text_color(self, text: str) -> QColor:
        if not self.displayText() and text == self.placeholderText():
            return self.palette().placeholderText().color()
        return self.palette().text().color()

    def _draw_faded_text(self, painter: QPainter, rect: QRectF, text: str, color: QColor) -> None:
        if rect.width() <= 0 or rect.height() <= 0:
            return

        ratio = max(1.0, self.devicePixelRatioF())
        pixmap = QPixmap(
            max(1, ceil(rect.width() * ratio)),
            max(1, ceil(rect.height() * ratio)),
        )
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        layer = QPainter(pixmap)
        configure_painter(layer, text_antialias=True, smooth_pixmap=True)
        layer.setFont(self.font())
        local_rect = QRectF(0, 0, pixmap.width() / ratio, pixmap.height() / ratio)
        offset = self._overflow_animation_offset(text, local_rect)
        text_width = max(0.0, float(_text_render_width(self, (text,))))
        if offset > 0.0:
            layer.save()
            layer.setClipRect(local_rect)
            layer.translate(-offset, 0.0)
            self._draw_themed_text_path(
                layer,
                QRectF(0.0, 0.0, max(local_rect.width(), text_width), local_rect.height()),
                self.alignment(),
                text,
                color,
            )
            layer.restore()
        else:
            self._draw_themed_text_path(layer, local_rect, self.alignment(), text, color)
        layer.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        layer.fillRect(
            local_rect,
            QBrush(self._fade_mask_gradient(local_rect, offset, max(0.0, text_width - local_rect.width()))),
        )
        layer.end()

        painter.drawPixmap(rect.topLeft(), pixmap)

    def _fade_mask_gradient(self, rect: QRectF, offset: float, max_scroll: float) -> QLinearGradient:
        width = max(1.0, rect.width())
        fade = min(36.0, max(10.0, width * 0.28), width / 2.0)
        opaque = QColor(0, 0, 0, 255)
        transparent = QColor(0, 0, 0, 0)

        gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        if max_scroll > 0.5:
            fade_stop = min(0.48, max(0.0, fade / width))
            left_alpha = 0 if offset > 0.5 else 255
            right_alpha = 0 if offset < (max_scroll - 0.5) else 255
            gradient.setColorAt(0.0, QColor(0, 0, 0, left_alpha))
            gradient.setColorAt(fade_stop, opaque)
            gradient.setColorAt(max(fade_stop, 1.0 - fade_stop), opaque)
            gradient.setColorAt(1.0, QColor(0, 0, 0, right_alpha))
            return gradient

        alignment = self.alignment()
        if alignment & Qt.AlignmentFlag.AlignRight:
            fade_stop = min(1.0, fade / width)
            gradient.setColorAt(0.0, transparent)
            gradient.setColorAt(fade_stop, opaque)
            gradient.setColorAt(1.0, opaque)
        elif alignment & Qt.AlignmentFlag.AlignHCenter:
            fade_stop = min(0.5, fade / width)
            gradient.setColorAt(0.0, transparent)
            gradient.setColorAt(fade_stop, opaque)
            gradient.setColorAt(1.0 - fade_stop, opaque)
            gradient.setColorAt(1.0, transparent)
        else:
            fade_stop = max(0.0, 1.0 - fade / width)
            gradient.setColorAt(0.0, opaque)
            gradient.setColorAt(fade_stop, opaque)
            gradient.setColorAt(1.0, transparent)
        return gradient

    def _set_overflow_hover_active(self, active: bool) -> None:
        target = bool(active)
        if self._overflow_hover_active == target:
            return
        self._overflow_hover_active = target
        self._overflow_animation_started_at = monotonic()
        if target:
            self._start_overflow_animation_timer()
        else:
            self._stop_overflow_animation_timer()
        self.update()

    def _start_overflow_animation_timer(self) -> None:
        if self._overflow_animation_timer_id:
            return
        self._overflow_animation_timer_id = int(self.startTimer(16, Qt.TimerType.PreciseTimer))

    def _stop_overflow_animation_timer(self) -> None:
        if self._overflow_animation_timer_id <= 0:
            return
        self.killTimer(self._overflow_animation_timer_id)
        self._overflow_animation_timer_id = 0

    def _handle_overflow_timer_event(self, event: QTimerEvent) -> bool:
        timer_id = int(self._overflow_animation_timer_id or 0)
        if timer_id <= 0 or event.timerId() != timer_id:
            return False
        self.update()
        return True

    def _overflow_animation_offset(self, text: str, rect: QRectF) -> float:
        if not self._overflow_hover_active:
            return 0.0

        viewport_width = max(0.0, float(rect.width()))
        content_width = max(0.0, float(_text_render_width(self, (text,))))
        max_scroll = max(0.0, content_width - viewport_width)
        if max_scroll <= 1.0:
            return 0.0

        elapsed = max(0.0, monotonic() - float(self._overflow_animation_started_at or 0.0))
        travel_duration = max(0.01, max_scroll / self._OVERFLOW_SCROLL_SPEED)
        cycle_duration = (
            self._OVERFLOW_SCROLL_DELAY
            + travel_duration
            + self._OVERFLOW_SCROLL_EDGE_PAUSE
            + travel_duration
            + self._OVERFLOW_SCROLL_EDGE_PAUSE
        )
        phase = elapsed % cycle_duration
        if phase < self._OVERFLOW_SCROLL_DELAY:
            return 0.0
        phase -= self._OVERFLOW_SCROLL_DELAY

        if phase < travel_duration:
            return max_scroll * self._overflow_scroll_progress(phase / travel_duration)
        phase -= travel_duration

        if phase < self._OVERFLOW_SCROLL_EDGE_PAUSE:
            return max_scroll
        phase -= self._OVERFLOW_SCROLL_EDGE_PAUSE

        if phase < travel_duration:
            return max_scroll * (1.0 - self._overflow_scroll_progress(phase / travel_duration))
        return 0.0

    def _overflow_scroll_progress(self, progress: float) -> float:
        clamped = max(0.0, min(1.0, float(progress)))
        return clamped * clamped * (3.0 - (2.0 * clamped))


class MTSpinBox(BoxThemeMixin, QSpinBox):
    PAINTED_BOX_THEME = False

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFrame(False)
        self.lineEdit().setTextMargins(0, 0, 0, 0)
        self.init_box_theme()

        if obj_name:
            self.setObjectName(obj_name)

    def sizeHint(self) -> QSize:
        return self._content_size_hint()

    def minimumSizeHint(self) -> QSize:
        return self._content_size_hint()

    def _content_size_hint(self) -> QSize:
        return _spin_box_content_size_hint(
            self,
            (
                self.textFromValue(self.minimum()),
                self.textFromValue(self.maximum()),
            ),
        )

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        self.clearFocus()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.has_box_theme():
            painter = new_widget_painter(self)
            self.draw_box_theme(painter)
            painter.end()
        super().paintEvent(event)


class MTDoubleSpinBox(BoxThemeMixin, QDoubleSpinBox):
    PAINTED_BOX_THEME = False

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFrame(False)
        self.lineEdit().setTextMargins(0, 0, 0, 0)
        self.init_box_theme()

        if obj_name:
            self.setObjectName(obj_name)

    def sizeHint(self) -> QSize:
        return self._content_size_hint()

    def minimumSizeHint(self) -> QSize:
        return self._content_size_hint()

    def _content_size_hint(self) -> QSize:
        return _spin_box_content_size_hint(
            self,
            (
                self.textFromValue(self.minimum()),
                self.textFromValue(self.maximum()),
            ),
        )

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        self.clearFocus()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.has_box_theme():
            painter = new_widget_painter(self)
            self.draw_box_theme(painter)
            painter.end()
        super().paintEvent(event)
