from collections.abc import Callable
from copy import deepcopy
from math import ceil
from time import monotonic
from typing import TYPE_CHECKING, TypeAlias, cast

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, QTimerEvent
from PySide6.QtGui import QBrush, QColor, QEnterEvent, QFont, QFontMetrics, QFontMetricsF, QIcon, QLinearGradient, QPaintEvent, QPainter, QPainterPath, QPainterPathStroker, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QStyle, QWidget
from PySide6.QtGui import QPalette

from src.translation.mixin import TranslatableMixin
from src.ui.painting import configure_painter, draw_widget_background
from src.ui.widgets.custom.box import BoxThemeMixin

TextEffectState: TypeAlias = dict[str, object]
TextLayerDrawer: TypeAlias = Callable[[QPainter, QRectF], None]

if TYPE_CHECKING:
    class _TextEffectBase:
        def text(self) -> str: ...
        def font(self) -> QFont: ...
        def fontMetrics(self) -> QFontMetrics: ...
        def palette(self) -> QPalette: ...
        def contentsRect(self) -> QRect: ...
        def updateGeometry(self) -> None: ...
        def update(self, *args: object) -> None: ...
        def startTimer(self, interval: int, timerType: Qt.TimerType = Qt.TimerType.CoarseTimer) -> int: ...
        def killTimer(self, timerId: object) -> None: ...
        def alignment(self) -> Qt.AlignmentFlag: ...
        def property(self, name: str) -> object: ...
        def style(self) -> QStyle: ...
        def has_box_theme(self) -> bool: ...
        def draw_box_theme(self, painter: QPainter) -> None: ...
else:
    class _TextEffectBase:
        pass


def _state_mapping(value: object) -> TextEffectState | None:
    return cast(TextEffectState, value) if isinstance(value, dict) else None


def _state_str(state: TextEffectState | None, key: str, default: str = '') -> str:
    if state is None:
        return default
    value = state.get(key)
    return str(value) if value is not None else default


def _state_qcolor(state: TextEffectState | None, key: str) -> QColor | None:
    if state is None:
        return None
    value = state.get(key)
    return value if isinstance(value, QColor) else None


def _state_qsize(state: TextEffectState | None, key: str) -> QSize | None:
    if state is None:
        return None
    value = state.get(key)
    if isinstance(value, QSize) and value.isValid():
        return QSize(value)
    return None


def _state_qpixmap(state: TextEffectState | None, key: str) -> QPixmap | None:
    if state is None:
        return None
    value = state.get(key)
    if isinstance(value, QPixmap) and not value.isNull():
        return QPixmap(value)
    return None


def _state_float(state: TextEffectState | None, key: str, default: float = 0.0) -> float:
    if state is None:
        return default
    value = state.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().lower().removesuffix('px').strip()
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


class TextEffectMixin(_TextEffectBase):
    _OVERFLOW_SCROLL_DELAY = 0.55
    _OVERFLOW_SCROLL_EDGE_PAUSE = 0.85
    _OVERFLOW_SCROLL_SPEED = 28.0

    def init_text_effects(self) -> None:
        self._text_shadow: TextEffectState | None = None
        self._text_border: TextEffectState | None = None
        self._text_icon: TextEffectState | None = None
        self._default_text_icon: TextEffectState | None = None
        self._default_text_icon_captured = False
        self._text_spacing: float | None = None
        self._force_text_path_render = False
        self._text_effect_cache: TextEffectState | None = None
        self._overflow_hover_active = False
        self._overflow_animation_timer_id = 0
        self._overflow_animation_started_at = 0.0

    def set_text_icon(
        self,
        *,
        source: str,
        align: str = 'left',
        size: QSize | None = None,
        spacing: float = 4.0,
        color: QColor | None = None,
    ) -> bool:
        icon = QIcon(str(source))
        if icon.isNull():
            return False

        align = str(align or 'left').strip().lower().replace('_', '-')
        if align not in {'left', 'right', 'top', 'bottom'}:
            align = 'left'

        requested_size = QSize(size) if isinstance(size, QSize) and size.isValid() else QSize()
        if requested_size.isValid():
            pixmap = icon.pixmap(requested_size)
            icon_size = requested_size
        else:
            pixmap = QPixmap(str(source))
            if pixmap.isNull():
                icon_size = icon.actualSize(QSize(16, 16))
                if not icon_size.isValid() or icon_size.isEmpty():
                    icon_size = QSize(16, 16)
                pixmap = icon.pixmap(icon_size)
            else:
                icon_size = pixmap.size()
        if pixmap.isNull():
            return False
        if isinstance(color, QColor) and color.isValid() and color.alpha() > 0:
            pixmap = self._tinted_icon_pixmap(pixmap, color)

        self._text_icon = {
            'source': str(source),
            'pixmap': pixmap,
            'align': align,
            'size': icon_size,
            'spacing': max(0.0, float(spacing)),
        }
        self.updateGeometry()
        self.update()
        return True

    def _tinted_icon_pixmap(self, pixmap: QPixmap, color: QColor) -> QPixmap:
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted

    def clear_text_icon(self) -> None:
        self._text_icon = None
        self.updateGeometry()
        self.update()

    def text_icon_state(self) -> TextEffectState | None:
        return self._clone_text_icon_state(_state_mapping(getattr(self, '_text_icon', None)))

    def default_text_icon_state(self) -> TextEffectState | None:
        return self._clone_text_icon_state(_state_mapping(getattr(self, '_default_text_icon', None)))

    def capture_default_text_icon_state(self) -> None:
        if bool(getattr(self, '_default_text_icon_captured', False)):
            return
        self._default_text_icon = self.text_icon_state()
        self._default_text_icon_captured = True

    def restore_default_text_icon_state(self) -> None:
        self._text_icon = self._clone_text_icon_state(_state_mapping(getattr(self, '_default_text_icon', None)))
        self.updateGeometry()
        self.update()

    def restore_text_icon_state(self, state: TextEffectState | None) -> None:
        self._text_icon = self._clone_text_icon_state(state)
        self.updateGeometry()
        self.update()

    def _clone_text_icon_state(self, icon: TextEffectState | None) -> TextEffectState | None:
        if icon is None:
            return None

        cloned: TextEffectState = {
            'source': _state_str(icon, 'source'),
            'align': _state_str(icon, 'align', 'left'),
            'spacing': _state_float(icon, 'spacing'),
        }

        pixmap = _state_qpixmap(icon, 'pixmap')
        cloned['pixmap'] = pixmap if pixmap is not None else QPixmap()
        size = _state_qsize(icon, 'size')
        cloned['size'] = size if size is not None else QSize()
        return cloned

    def set_text_border(self, *, color: QColor, width: float = 1.0, style: str = 'solid') -> None:
        self._text_border = {
            'color': QColor(color),
            'width': max(0.0, float(width)),
            'style': str(style or 'solid').strip().lower(),
        }
        self._invalidate_text_effect_cache()
        self.update()

    def clear_text_border(self) -> None:
        self._text_border = None
        self._invalidate_text_effect_cache()
        self.update()

    def text_border_state(self) -> TextEffectState | None:
        border = _state_mapping(getattr(self, '_text_border', None))
        return deepcopy(border) if border is not None else None

    def restore_text_border_state(self, state: TextEffectState | None) -> None:
        self._text_border = deepcopy(state) if state is not None else None
        self._invalidate_text_effect_cache()
        self.update()

    def set_text_border_color(self, value: QColor | str) -> bool:
        border = _state_mapping(getattr(self, '_text_border', None))
        if border is None:
            border = cast(TextEffectState, {
                'color': QColor(Qt.GlobalColor.transparent),
                'width': 1.0,
                'style': 'solid',
            })
            self._text_border = border

        color = QColor(value)
        if not color.isValid():
            return False

        border['color'] = color
        self.update()
        return True

    def set_text_border_width(self, value: int | float | str) -> bool:
        border = _state_mapping(getattr(self, '_text_border', None))
        if border is None:
            border = cast(TextEffectState, {
                'color': QColor(Qt.GlobalColor.transparent),
                'width': 0.0,
                'style': 'solid',
            })
            self._text_border = border

        try:
            width = float(str(value).strip().lower().removesuffix('px').strip())
        except (TypeError, ValueError):
            return False

        border['width'] = max(0.0, width)
        self._invalidate_text_effect_cache()
        self.update()
        return True

    def set_text_icon_color(self, value: QColor | str) -> bool:
        icon = self.text_icon_state()
        if icon is None:
            icon = self.default_text_icon_state()
        if icon is None:
            return False

        source = _state_str(icon, 'source').strip()
        if not source:
            return False

        color = QColor(value)
        if not color.isValid():
            return False

        requested_size = _state_qsize(icon, 'size')
        spacing = _state_float(icon, 'spacing')
        align = _state_str(icon, 'align', 'left')
        return self.set_text_icon(
            source=source,
            align=align,
            size=requested_size,
            spacing=spacing,
            color=color,
        )

    def set_text_shadow(self, *, color: QColor, x: float = 0.0, y: float = 0.0, blur: float = 0.0) -> None:
        self._text_shadow = {
            'color': QColor(color),
            'x': float(x),
            'y': float(y),
            'blur': float(blur),
        }
        self._invalidate_text_effect_cache()
        self.update()

    def clear_text_shadow(self) -> None:
        self._text_shadow = None
        self._invalidate_text_effect_cache()
        self.update()

    def set_text_spacing(self, value: float) -> None:
        self._text_spacing = float(value)
        self._invalidate_text_effect_cache()
        self.updateGeometry()
        self.update()

    def clear_text_spacing(self) -> None:
        self._text_spacing = None
        self._invalidate_text_effect_cache()
        self.updateGeometry()
        self.update()

    def _text_spacing_value(self) -> float:
        value = getattr(self, '_text_spacing', None)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def _has_text_spacing(self) -> bool:
        return abs(self._text_spacing_value()) > 0.001

    def _has_text_shadow(self) -> bool:
        shadow = _state_mapping(getattr(self, '_text_shadow', None))
        color = _state_qcolor(shadow, 'color')
        return isinstance(color, QColor) and color.isValid() and color.alpha() > 0

    def _has_text_border(self) -> bool:
        border = _state_mapping(getattr(self, '_text_border', None))
        color = _state_qcolor(border, 'color')
        width = _state_float(border, 'width')
        return (
            isinstance(color, QColor)
            and color.isValid()
            and color.alpha() > 0
            and width > 0.0
        )

    def _has_text_effect(self) -> bool:
        return self._has_text_shadow() or self._has_text_border()

    def _has_custom_text_render(self) -> bool:
        return self._force_text_path_render_enabled() or self._has_text_effect() or self._has_text_spacing()

    def _force_text_path_render_enabled(self) -> bool:
        return bool(getattr(self, '_force_text_path_render', False))

    def set_force_text_path_render(self, enabled: bool) -> None:
        self._force_text_path_render = bool(enabled)
        self._invalidate_text_effect_cache()
        self.update()

    def _has_text_icon(self) -> bool:
        icon = _state_mapping(getattr(self, '_text_icon', None))
        pixmap = _state_qpixmap(icon, 'pixmap')
        size = _state_qsize(icon, 'size')
        return (
            isinstance(pixmap, QPixmap)
            and not pixmap.isNull()
            and isinstance(size, QSize)
            and size.width() > 0
            and size.height() > 0
        )

    def _visual_text_size(self, text: str) -> QSize:
        if not text:
            return QSize(0, 0)

        metrics = QFontMetricsF(self.font())
        text_height = metrics.height()
        baseline = metrics.ascent()
        path = QPainterPath()

        if not self._has_text_spacing() or len(text) <= 1:
            path.addText(QPointF(0.0, baseline), self.font(), text)
        else:
            cursor_x = 0.0
            spacing = self._text_spacing_value()
            for char in text:
                path.addText(QPointF(cursor_x, baseline), self.font(), char)
                cursor_x += metrics.horizontalAdvance(char) + spacing

        bounds = path.boundingRect()
        advance_width = max(0.0, float(metrics.horizontalAdvance(text)) + (self._text_spacing_value() * max(0, len(text) - 1)))
        left_overhang = max(0.0, -bounds.left())
        right_extent = max(advance_width, bounds.right())
        width = left_overhang + right_extent
        height = max(text_height, bounds.height())

        border = _state_mapping(getattr(self, '_text_border', None))
        border_width = _state_float(border, 'width')
        if border_width > 0.0:
            width += border_width
            height += border_width

        shadow = _state_mapping(getattr(self, '_text_shadow', None))
        if shadow is not None:
            width += abs(_state_float(shadow, 'x'))
            height += abs(_state_float(shadow, 'y'))

        return QSize(
            max(1, int(ceil(width))),
            max(1, int(ceil(height))),
        )

    def _themed_visual_content_size(self, text: str, icon_size: QSize | None = None) -> QSize:
        visual_text = self._visual_text_size(text)
        text_width = visual_text.width()
        text_height = visual_text.height()
        if icon_size is None:
            icon_size = self._text_icon_size()
        icon_width = icon_size.width() if icon_size is not None and icon_size.isValid() else 0
        icon_height = icon_size.height() if icon_size is not None and icon_size.isValid() else 0
        spacing = self._text_icon_spacing() if text_width and icon_width else 0.0

        if self._text_icon_align() in {'top', 'bottom'}:
            return QSize(
                max(1, int(round(max(text_width, icon_width)))),
                max(1, int(round(icon_height + spacing + text_height))),
            )

        return QSize(
            max(1, int(round(icon_width + spacing + text_width))),
            max(1, int(round(max(text_height, icon_height)))),
        )

    def _draw_themed_icon_text(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
        text_color: QColor,
    ) -> None:
        icon = _state_mapping(getattr(self, '_text_icon', None))
        pixmap = _state_qpixmap(icon, 'pixmap')
        icon_size = self._text_icon_size()
        if not isinstance(pixmap, QPixmap) or pixmap.isNull() or icon_size is None:
            self._draw_themed_text(painter, rect, alignment, text, text_color)
            return

        content_size = self._themed_visual_content_size(text, icon_size)
        content_rect = self._aligned_rect(rect, content_size.width(), content_size.height(), alignment)
        spacing = self._text_icon_spacing() if text else 0.0
        align = self._text_icon_align()

        visual_text = self._visual_text_size(text)
        text_width = visual_text.width()
        text_height = visual_text.height()
        icon_rect = QRectF(content_rect.left(), content_rect.top(), icon_size.width(), icon_size.height())
        text_rect = QRectF(content_rect.left(), content_rect.top(), max(0, text_width), max(1, text_height))

        match align:
            case 'right':
                text_rect.moveLeft(content_rect.left())
                text_rect.moveTop(content_rect.top() + max(0.0, (content_rect.height() - text_rect.height()) / 2.0))
                icon_rect.moveLeft(text_rect.right() + spacing)
                icon_rect.moveTop(content_rect.top() + max(0.0, (content_rect.height() - icon_rect.height()) / 2.0))
            case 'top':
                icon_rect.moveLeft(content_rect.left() + max(0.0, (content_rect.width() - icon_rect.width()) / 2.0))
                icon_rect.moveTop(content_rect.top())
                text_rect.moveLeft(content_rect.left())
                text_rect.setWidth(content_rect.width())
                text_rect.moveTop(icon_rect.bottom() + spacing)
            case 'bottom':
                text_rect.moveLeft(content_rect.left())
                text_rect.setWidth(content_rect.width())
                text_rect.moveTop(content_rect.top())
                icon_rect.moveLeft(content_rect.left() + max(0.0, (content_rect.width() - icon_rect.width()) / 2.0))
                icon_rect.moveTop(text_rect.bottom() + spacing)
            case _:
                icon_rect.moveLeft(content_rect.left())
                icon_rect.moveTop(content_rect.top() + max(0.0, (content_rect.height() - icon_rect.height()) / 2.0))
                text_rect.moveLeft(icon_rect.right() + spacing)
                text_rect.moveTop(content_rect.top() + max(0.0, (content_rect.height() - text_rect.height()) / 2.0))

        painter.drawPixmap(icon_rect.toRect(), pixmap)
        if text:
            self._draw_themed_text(painter, text_rect, self._text_only_alignment(alignment, align), text, text_color)

    def _aligned_rect(self, rect: QRectF, width: float, height: float, alignment: Qt.AlignmentFlag) -> QRectF:
        if alignment & Qt.AlignmentFlag.AlignRight:
            x = rect.right() - width
        elif alignment & Qt.AlignmentFlag.AlignHCenter:
            x = rect.left() + max(0.0, (rect.width() - width) / 2.0)
        else:
            x = rect.left()

        if alignment & Qt.AlignmentFlag.AlignBottom:
            y = rect.bottom() - height
        elif alignment & Qt.AlignmentFlag.AlignTop:
            y = rect.top()
        else:
            y = rect.top() + max(0.0, (rect.height() - height) / 2.0)
        return QRectF(x, y, width, height)

    def _text_only_alignment(self, alignment: Qt.AlignmentFlag, icon_align: str) -> Qt.AlignmentFlag:
        result = Qt.AlignmentFlag(0)
        if icon_align in {'top', 'bottom'}:
            if alignment & Qt.AlignmentFlag.AlignRight:
                result |= Qt.AlignmentFlag.AlignRight
            elif alignment & Qt.AlignmentFlag.AlignHCenter:
                result |= Qt.AlignmentFlag.AlignHCenter
            else:
                result |= Qt.AlignmentFlag.AlignLeft
        else:
            result |= Qt.AlignmentFlag.AlignLeft

        if icon_align in {'left', 'right'}:
            if alignment & Qt.AlignmentFlag.AlignBottom:
                result |= Qt.AlignmentFlag.AlignBottom
            elif alignment & Qt.AlignmentFlag.AlignTop:
                result |= Qt.AlignmentFlag.AlignTop
            else:
                result |= Qt.AlignmentFlag.AlignVCenter
        else:
            result |= Qt.AlignmentFlag.AlignTop
        return result

    def _text_icon_size(self) -> QSize | None:
        return _state_qsize(_state_mapping(getattr(self, '_text_icon', None)), 'size')

    def _text_icon_spacing(self) -> float:
        icon = _state_mapping(getattr(self, '_text_icon', None))
        return max(0.0, _state_float(icon, 'spacing'))

    def _text_icon_align(self) -> str:
        icon = _state_mapping(getattr(self, '_text_icon', None))
        align = _state_str(icon, 'align', 'left')
        align = str(align or 'left').strip().lower().replace('_', '-')
        return align if align in {'left', 'right', 'top', 'bottom'} else 'left'

    def _text_render_width(self, text: str) -> float:
        if not text:
            return 0.0
        return max(
            0.0,
            float(self.fontMetrics().horizontalAdvance(text)) + (self._text_spacing_value() * max(0, len(text) - 1)),
        )

    def _draw_shadowed_text(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
        text_color: QColor,
    ) -> None:
        if not text:
            return

        if self._should_composite_text_layer(text, rect):
            self._draw_faded_text_layer(
                painter,
                rect,
                text,
                lambda layer_painter, layer_rect: self._draw_shadowed_text_layer(
                    layer_painter,
                    layer_rect,
                    alignment,
                    text,
                    text_color,
                ),
            )
            return

        self._draw_shadowed_text_layer(painter, rect, alignment, text, text_color)

    def _draw_shadowed_text_layer(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
        text_color: QColor,
    ) -> None:
        shadow = _state_mapping(getattr(self, '_text_shadow', None))
        if shadow is not None:
            shadow_color = _state_qcolor(shadow, 'color')
            if isinstance(shadow_color, QColor) and shadow_color.isValid() and shadow_color.alpha() > 0:
                offset_rect = rect.translated(_state_float(shadow, 'x'), _state_float(shadow, 'y'))
                painter.setPen(shadow_color)
                painter.drawText(offset_rect, alignment, text)

        painter.setPen(text_color)
        painter.drawText(rect, alignment, text)

    def _draw_themed_text(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
        text_color: QColor,
    ) -> None:
        if not text:
            return

        if not self._force_text_path_render_enabled() and not self._has_text_spacing() and not self._has_text_border():
            self._draw_shadowed_text(painter, rect, alignment, text, text_color)
            return

        if self._should_composite_text_layer(text, rect):
            self._draw_faded_text_layer(
                painter,
                rect,
                text,
                lambda layer_painter, layer_rect: self._draw_themed_text_path(
                    layer_painter,
                    layer_rect,
                    alignment,
                    text,
                    text_color,
                ),
            )
            return

        self._draw_themed_text_path(painter, rect, alignment, text, text_color)

    def _draw_themed_text_path(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
        text_color: QColor,
    ) -> None:
        if not text:
            return

        text_path = self._cached_text_path(painter, rect, alignment, text)
        shadow = _state_mapping(getattr(self, '_text_shadow', None))
        if shadow is not None:
            shadow_color = _state_qcolor(shadow, 'color')
            if isinstance(shadow_color, QColor) and shadow_color.isValid() and shadow_color.alpha() > 0:
                shadow_path = QPainterPath(text_path)
                shadow_path.translate(_state_float(shadow, 'x'), _state_float(shadow, 'y'))
                painter.fillPath(shadow_path, QBrush(shadow_color))

        border = _state_mapping(getattr(self, '_text_border', None))
        if border is not None:
            border_color = _state_qcolor(border, 'color')
            border_width = _state_float(border, 'width')
            if isinstance(border_color, QColor) and border_color.isValid() and border_color.alpha() > 0 and border_width > 0.0:
                self._draw_text_outline(
                    painter,
                    text_path,
                    fill=QBrush(text_color),
                    border_color=border_color,
                    border_width=border_width,
                    border_style=_state_str(border, 'style', 'solid'),
                )
                return

        painter.fillPath(text_path, QBrush(text_color))

    def _cached_text_path(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
    ) -> QPainterPath:
        key = self._text_cache_key(painter, rect, alignment, text)
        cache = _state_mapping(getattr(self, '_text_effect_cache', None))
        cached_path = cache.get('path') if cache is not None else None
        if cache is not None and cache.get('key') == key and isinstance(cached_path, QPainterPath):
            return QPainterPath(cached_path)

        path = self._text_path(painter, rect, alignment, text)
        self._text_effect_cache = {
            'key': key,
            'path': QPainterPath(path),
        }
        return path

    def _draw_text_outline(
        self,
        painter: QPainter,
        text_path: QPainterPath,
        *,
        fill: QBrush,
        border_color: QColor,
        border_width: float,
        border_style: object = 'solid',
    ) -> None:
        pen_style = self._pen_style(border_style)
        if pen_style == Qt.PenStyle.NoPen:
            painter.fillPath(text_path, fill)
            return

        outline = self._cached_text_outline(text_path, border_width, pen_style)
        painter.fillPath(outline, QBrush(border_color))
        painter.fillPath(text_path, fill)

    def _cached_text_outline(
        self,
        text_path: QPainterPath,
        border_width: float,
        pen_style: Qt.PenStyle,
    ) -> QPainterPath:
        cache = _state_mapping(getattr(self, '_text_effect_cache', None))
        path_bounds = text_path.boundingRect()
        key = (
            'outline',
            float(border_width),
            pen_style.value if hasattr(pen_style, 'value') else str(pen_style),
            round(path_bounds.left(), 2),
            round(path_bounds.top(), 2),
            round(path_bounds.width(), 2),
            round(path_bounds.height(), 2),
        )
        if (
            cache is not None
            and cache.get('outline_key') == key
            and isinstance(cache.get('outline'), QPainterPath)
        ):
            outline = cache.get('outline')
            if isinstance(outline, QPainterPath):
                return QPainterPath(outline)

        stroker = QPainterPathStroker()
        stroker.setWidth(max(0.0, float(border_width)))
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setDashPattern(pen_style)

        outline = stroker.createStroke(text_path).subtracted(text_path)
        if cache is None:
            cache = {}
            self._text_effect_cache = cache
        cache['outline_key'] = key
        cache['outline'] = QPainterPath(outline)
        return outline

    def _text_path(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
    ) -> QPainterPath:
        metrics = QFontMetricsF(painter.font())
        text_width = max(0.0, metrics.horizontalAdvance(text) + (self._text_spacing_value() * max(0, len(text) - 1)))
        text_height = metrics.height()

        if alignment & Qt.AlignmentFlag.AlignRight:
            x = rect.right() - text_width
        elif alignment & Qt.AlignmentFlag.AlignHCenter:
            x = rect.left() + max(0.0, (rect.width() - text_width) / 2.0)
        else:
            x = rect.left()

        if alignment & Qt.AlignmentFlag.AlignBottom:
            y = rect.bottom() - metrics.descent()
        elif alignment & Qt.AlignmentFlag.AlignTop:
            y = rect.top() + metrics.ascent()
        else:
            y = rect.top() + max(0.0, (rect.height() - text_height) / 2.0) + metrics.ascent()

        path = QPainterPath()
        if not self._has_text_spacing() or len(text) <= 1:
            path.addText(QPointF(x, y), painter.font(), text)
            return path

        cursor_x = x
        spacing = self._text_spacing_value()
        for char in text:
            path.addText(QPointF(cursor_x, y), painter.font(), char)
            cursor_x += metrics.horizontalAdvance(char) + spacing
        return path

    def _text_cache_key(
        self,
        painter: QPainter,
        rect: QRectF,
        alignment: Qt.AlignmentFlag,
        text: str,
    ) -> tuple[object, ...]:
        font = painter.font()
        return (
            text,
            font.toString(),
            round(self._text_spacing_value(), 3),
            int(alignment),
            round(rect.left(), 2),
            round(rect.top(), 2),
            round(rect.width(), 2),
            round(rect.height(), 2),
        )

    def _invalidate_text_effect_cache(self) -> None:
        self._text_effect_cache = None

    def _pen_style(self, value: object) -> Qt.PenStyle:
        match str(value or 'solid').strip().lower().replace('_', '-'):
            case 'none' | 'no' | 'transparent':
                return Qt.PenStyle.NoPen
            case 'dash' | 'dashed':
                return Qt.PenStyle.DashLine
            case 'dot' | 'dotted':
                return Qt.PenStyle.DotLine
            case 'dash-dot':
                return Qt.PenStyle.DashDotLine
            case 'dash-dot-dot':
                return Qt.PenStyle.DashDotDotLine
            case _:
                return Qt.PenStyle.SolidLine

    def _text_overflows_rect(self, text: str, rect: QRectF) -> bool:
        return bool(text) and rect.width() > 0.0 and self._text_render_width(text) > rect.width()

    def _should_composite_text_layer(self, text: str, rect: QRectF) -> bool:
        return bool(text) and rect.width() > 0.0 and rect.height() > 0.0

    def _set_overflow_hover_active(self, active: bool) -> None:
        active = bool(active)
        if getattr(self, '_overflow_hover_active', False) == active:
            return

        self._overflow_hover_active = active
        self._overflow_animation_started_at = monotonic()
        if active:
            self._start_overflow_animation_timer()
        else:
            self._stop_overflow_animation_timer()
        self.update()

    def _start_overflow_animation_timer(self) -> None:
        if getattr(self, '_overflow_animation_timer_id', 0):
            return
        self._overflow_animation_timer_id = int(self.startTimer(16, Qt.TimerType.PreciseTimer))

    def _stop_overflow_animation_timer(self) -> None:
        timer_id = int(getattr(self, '_overflow_animation_timer_id', 0) or 0)
        if timer_id <= 0:
            return
        self.killTimer(timer_id)
        self._overflow_animation_timer_id = 0

    def _handle_overflow_timer_event(self, event: QTimerEvent) -> bool:
        timer_id = int(getattr(self, '_overflow_animation_timer_id', 0) or 0)
        if timer_id <= 0 or event.timerId() != timer_id:
            return False
        self.update()
        return True

    def _overflow_animation_offset(self, text: str, rect: QRectF) -> float:
        if not getattr(self, '_overflow_hover_active', False):
            return 0.0

        viewport_width = max(0.0, float(rect.width()))
        content_width = max(0.0, self._text_render_width(text))
        max_scroll = max(0.0, content_width - viewport_width)
        if max_scroll <= 1.0:
            return 0.0

        elapsed = max(0.0, monotonic() - float(getattr(self, '_overflow_animation_started_at', 0.0) or 0.0))
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

    def _build_overflow_mask(self, width: float, offset: float, max_scroll: float) -> QLinearGradient:
        fade_width = min(width, max(10.0, min(36.0, width * 0.28)))
        edge_ratio = min(0.48, max(0.0, fade_width / max(1.0, width)))
        mask = QLinearGradient(0.0, 0.0, width, 0.0)
        left_edge_alpha = 0 if offset > 0.5 else 255
        right_edge_alpha = 0 if offset < (max_scroll - 0.5) else 255
        mask.setColorAt(0.0, QColor(0, 0, 0, left_edge_alpha))
        mask.setColorAt(edge_ratio, QColor(0, 0, 0, 255))
        mask.setColorAt(max(edge_ratio, 1.0 - edge_ratio), QColor(0, 0, 0, 255))
        mask.setColorAt(1.0, QColor(0, 0, 0, right_edge_alpha))
        return mask

    def _draw_faded_text_layer(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        draw_layer: TextLayerDrawer,
    ) -> None:
        width = max(1, int(ceil(rect.width())))
        height = max(1, int(ceil(rect.height())))
        if width <= 1 or height <= 1:
            return

        device_ratio = max(1.0, float(painter.device().devicePixelRatioF()))
        pixmap = QPixmap(max(1, int(width * device_ratio)), max(1, int(height * device_ratio)))
        pixmap.setDevicePixelRatio(device_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        layer_painter = QPainter(pixmap)
        self._configure_themed_painter(layer_painter)
        layer_painter.setFont(painter.font())
        local_rect = QRectF(0.0, 0.0, float(width), float(height))
        offset = self._overflow_animation_offset(text, local_rect)
        if offset > 0.0:
            layer_painter.save()
            layer_painter.setClipRect(local_rect)
            layer_painter.translate(-offset, 0.0)
            draw_layer(layer_painter, QRectF(0.0, 0.0, max(float(width), self._text_render_width(text)), float(height)))
            layer_painter.restore()
        else:
            draw_layer(layer_painter, local_rect)

        layer_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        layer_painter.fillRect(
            local_rect,
            QBrush(self._build_overflow_mask(float(width), offset, max(0.0, self._text_render_width(text) - float(width)))),
        )
        layer_painter.end()

        painter.drawPixmap(QPointF(rect.left(), rect.top()), pixmap)

    def _configure_themed_painter(self, painter: QPainter) -> None:
        configure_painter(painter, text_antialias=True, smooth_pixmap=True)

    def _new_themed_painter(self) -> QPainter:
        painter = QPainter(cast(QWidget, self))
        self._configure_themed_painter(painter)
        return painter

    def _draw_themed_widget_background(self, painter: QPainter) -> None:
        draw_widget_background(cast(QWidget, self), painter)

    def _label_size_hint(self, base_hint: QSize) -> QSize:
        if not base_hint.isEmpty() and not self.text() and not self._has_text_icon():
            return base_hint
        if self._has_text_icon():
            return self._themed_visual_content_size(self.text())
        return self._visual_text_size(self.text())

    def _paint_themed_label(self, *, text_color: QColor) -> bool:
        text = self.text()
        text_rect = QRectF(self.contentsRect())
        text_overflows = self._text_overflows_rect(text, text_rect)

        if self.has_box_theme() and not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            painter = self._new_themed_painter()
            self.draw_box_theme(painter)
            painter.end()
            return False

        if not text.strip() and not self._has_text_icon():
            return False
        if not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            return False

        painter = self._new_themed_painter()
        self._draw_themed_widget_background(painter)
        painter.setFont(self.font())
        self._draw_themed_icon_text(
            painter,
            text_rect,
            self.alignment(),
            text,
            text_color,
        )
        painter.end()
        return True


class MTPlainLabel(BoxThemeMixin, TextEffectMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)

        if obj_name:
            self.setObjectName(obj_name)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event: QTimerEvent) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def sizeHint(self) -> QSize:
        return self._label_size_hint(super().sizeHint())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._paint_themed_label(text_color=self.palette().windowText().color()):
            return
        super().paintEvent(event)


class MTLabel(BoxThemeMixin, TextEffectMixin, TranslatableMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, tr_key: str, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(tr_key, parent)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)

        if obj_name:
            self.setObjectName(obj_name)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event: QTimerEvent) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def sizeHint(self) -> QSize:
        return self._label_size_hint(super().sizeHint())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._paint_themed_label(text_color=self.palette().windowText().color()):
            return
        super().paintEvent(event)


class MTButton(BoxThemeMixin, TextEffectMixin, TranslatableMixin, QPushButton):
    PAINTED_BOX_THEME = False

    def __init__(
        self,
        tr_key: str,
        parent: QWidget | None = None,
        checkable: bool = False,
        checked: bool = False,
        obj_name: str = '',
    ) -> None:
        super().__init__(tr_key, parent)
        self.setFlat(True)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if obj_name:
            self.setObjectName(obj_name)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event: QTimerEvent) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def sizeHint(self) -> QSize:
        return self._content_size_hint()

    def minimumSizeHint(self) -> QSize:
        return self._content_size_hint()

    def setAlignment(self, alignment: Qt.AlignmentFlag) -> None:
        self._alignment = alignment
        self.update()

    def alignment(self) -> Qt.AlignmentFlag:
        return self._alignment

    def _content_size_hint(self) -> QSize:
        if self._has_text_icon():
            content = self._themed_visual_content_size(self.text())
            text_width = content.width()
            text_height = content.height()
        else:
            visual_text = self._visual_text_size(self.text())
            text_width = visual_text.width()
            text_height = visual_text.height() if self.text() else 0
            icon = self.icon()
            icon_size = self.iconSize()
            icon_width = icon_size.width() if not icon.isNull() else 0
            icon_height = icon_size.height() if not icon.isNull() else 0
            spacing = 3 if text_width and icon_width else 0
            text_width = icon_width + spacing + text_width
            text_height = max(text_height, icon_height)
        left, top, right, bottom = self._theme_padding()
        return QSize(
            max(1, int(round(left + text_width + right))),
            max(1, int(round(top + text_height + bottom))),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = self._new_themed_painter()
        self._draw_themed_widget_background(painter)

        rect = self._padded_contents_rect()
        if self._has_text_icon():
            painter.setFont(self.font())
            self._draw_themed_icon_text(
                painter,
                rect,
                self._alignment,
                self.text(),
                self.palette().buttonText().color(),
            )
            painter.end()
            return

        icon = self.icon()
        icon_size = self.iconSize()
        spacing = 3 if not icon.isNull() and self.text() else 0
        if icon.isNull():
            if self.text():
                painter.setFont(self.font())
                self._draw_themed_text(
                    painter,
                    rect,
                    self._text_alignment(),
                    self.text(),
                    self.palette().buttonText().color(),
                )
            painter.end()
            return

        icon_width = icon_size.width() if not icon.isNull() else 0
        visual_text = self._visual_text_size(self.text())
        text_width = visual_text.width()
        content_width = icon_width + spacing + text_width
        x = self._content_left(rect, content_width)

        if not icon.isNull():
            y = self._content_top(rect, icon_size.height())
            icon.paint(
                painter,
                int(round(x)),
                int(round(y)),
                icon_size.width(),
                icon_size.height(),
            )
            x += icon_width + spacing

        if self.text():
            painter.setFont(self.font())
            available_width = max(0.0, rect.right() - x)
            text_rect = QRectF(x, rect.top(), available_width, rect.height())
            self._draw_themed_text(
                painter,
                text_rect,
                self._text_alignment(),
                self.text(),
                self.palette().buttonText().color(),
            )
        painter.end()

    def _content_left(self, rect: QRectF, content_width: int | float) -> float:
        alignment = self._alignment
        if alignment & Qt.AlignmentFlag.AlignRight:
            return rect.right() - float(content_width)
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            return rect.left() + max(0.0, (rect.width() - float(content_width)) / 2.0)
        return rect.left()

    def _content_top(self, rect: QRectF, content_height: int | float) -> float:
        alignment = self._alignment
        if alignment & Qt.AlignmentFlag.AlignBottom:
            return rect.bottom() - float(content_height)
        if alignment & Qt.AlignmentFlag.AlignVCenter:
            return rect.center().y() - (float(content_height) / 2.0)
        return rect.top()

    def _text_alignment(self) -> Qt.AlignmentFlag:
        alignment = Qt.AlignmentFlag(0)
        if self._alignment & Qt.AlignmentFlag.AlignRight:
            alignment |= Qt.AlignmentFlag.AlignRight
        elif self._alignment & Qt.AlignmentFlag.AlignHCenter:
            alignment |= Qt.AlignmentFlag.AlignHCenter
        else:
            alignment |= Qt.AlignmentFlag.AlignLeft

        if self._alignment & Qt.AlignmentFlag.AlignBottom:
            alignment |= Qt.AlignmentFlag.AlignBottom
        elif self._alignment & Qt.AlignmentFlag.AlignTop:
            alignment |= Qt.AlignmentFlag.AlignTop
        else:
            alignment |= Qt.AlignmentFlag.AlignVCenter
        return alignment

    def _padded_contents_rect(self) -> QRectF:
        left, top, right, bottom = self._theme_padding()
        rect = QRectF(self.contentsRect())
        return rect.adjusted(left, top, -right, -bottom)

    def _theme_padding(self) -> tuple[float, float, float, float]:
        padding = self.property('_themePaddingBox')
        if not isinstance(padding, (list, tuple)):
            return 0.0, 0.0, 0.0, 0.0
        padding_values = cast(list[object] | tuple[object, ...], padding)
        if len(padding_values) != 4:
            return 0.0, 0.0, 0.0, 0.0

        values: list[float] = []
        for value in padding_values:
            if isinstance(value, bool):
                return 0.0, 0.0, 0.0, 0.0
            if isinstance(value, (int, float)):
                values.append(max(0.0, float(value)))
                continue
            return 0.0, 0.0, 0.0, 0.0
        left, top, right, bottom = values
        return left, top, right, bottom
