from copy import deepcopy
from math import ceil
from time import monotonic

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QIcon, QLinearGradient, QPainter, QPainterPath, QPainterPathStroker, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QStyle, QStyleOption

from src.translation import TranslatableMixin
from src.ui.widgets.custom.box import BoxThemeMixin


class _TextEffectMixin:
    _OVERFLOW_SCROLL_DELAY = 0.55
    _OVERFLOW_SCROLL_EDGE_PAUSE = 0.85
    _OVERFLOW_SCROLL_SPEED = 28.0

    def init_text_effects(self) -> None:
        self._text_shadow = None
        self._text_border = None
        self._text_icon = None
        self._default_text_icon = None
        self._default_text_icon_captured = False
        self._text_spacing = None
        self._force_text_path_render = False
        self._text_effect_cache = None
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

    def text_icon_state(self) -> dict[str, object] | None:
        icon = getattr(self, '_text_icon', None)
        return self._clone_text_icon_state(icon) if isinstance(icon, dict) else None

    def default_text_icon_state(self) -> dict[str, object] | None:
        icon = getattr(self, '_default_text_icon', None)
        return self._clone_text_icon_state(icon) if isinstance(icon, dict) else None

    def capture_default_text_icon_state(self) -> None:
        if bool(getattr(self, '_default_text_icon_captured', False)):
            return
        self._default_text_icon = self.text_icon_state()
        self._default_text_icon_captured = True

    def restore_default_text_icon_state(self) -> None:
        icon = getattr(self, '_default_text_icon', None)
        self._text_icon = self._clone_text_icon_state(icon) if isinstance(icon, dict) else None
        self.updateGeometry()
        self.update()

    def restore_text_icon_state(self, state: dict[str, object] | None) -> None:
        self._text_icon = self._clone_text_icon_state(state) if isinstance(state, dict) else None
        self.updateGeometry()
        self.update()

    def _clone_text_icon_state(self, icon: dict[str, object] | None) -> dict[str, object] | None:
        if not isinstance(icon, dict):
            return None

        cloned: dict[str, object] = {
            'source': str(icon.get('source') or ''),
            'align': str(icon.get('align') or 'left'),
            'spacing': float(icon.get('spacing') or 0.0),
        }

        pixmap = icon.get('pixmap')
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            cloned['pixmap'] = QPixmap(pixmap)
        else:
            cloned['pixmap'] = QPixmap()

        size = icon.get('size')
        cloned['size'] = QSize(size) if isinstance(size, QSize) and size.isValid() else QSize()
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

    def text_border_state(self) -> dict[str, object] | None:
        border = getattr(self, '_text_border', None)
        return deepcopy(border) if isinstance(border, dict) else None

    def restore_text_border_state(self, state: dict[str, object] | None) -> None:
        self._text_border = deepcopy(state) if isinstance(state, dict) else None
        self._invalidate_text_effect_cache()
        self.update()

    def set_text_border_color(self, value: QColor | str) -> bool:
        border = getattr(self, '_text_border', None)
        if not isinstance(border, dict):
            border = {
                'color': QColor(Qt.GlobalColor.transparent),
                'width': 1.0,
                'style': 'solid',
            }
            self._text_border = border

        color = QColor(value)
        if not color.isValid():
            return False

        border['color'] = color
        self.update()
        return True

    def set_text_border_width(self, value: int | float | str) -> bool:
        border = getattr(self, '_text_border', None)
        if not isinstance(border, dict):
            border = {
                'color': QColor(Qt.GlobalColor.transparent),
                'width': 0.0,
                'style': 'solid',
            }
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
        if not isinstance(icon, dict):
            icon = self.default_text_icon_state()
        if not isinstance(icon, dict):
            return False

        source = str(icon.get('source') or '').strip()
        if not source:
            return False

        color = QColor(value)
        if not color.isValid():
            return False

        size = icon.get('size')
        requested_size = QSize(size) if isinstance(size, QSize) and size.isValid() else None
        spacing = float(icon.get('spacing') or 0.0)
        align = str(icon.get('align') or 'left')
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
        shadow = getattr(self, '_text_shadow', None)
        color = shadow.get('color') if isinstance(shadow, dict) else None
        return isinstance(color, QColor) and color.isValid() and color.alpha() > 0

    def _has_text_border(self) -> bool:
        border = getattr(self, '_text_border', None)
        color = border.get('color') if isinstance(border, dict) else None
        width = border.get('width') if isinstance(border, dict) else None
        return (
            isinstance(color, QColor)
            and color.isValid()
            and color.alpha() > 0
            and isinstance(width, (int, float))
            and float(width) > 0.0
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
        icon = getattr(self, '_text_icon', None)
        pixmap = icon.get('pixmap') if isinstance(icon, dict) else None
        size = icon.get('size') if isinstance(icon, dict) else None
        return (
            isinstance(pixmap, QPixmap)
            and not pixmap.isNull()
            and isinstance(size, QSize)
            and size.width() > 0
            and size.height() > 0
        )

    def _themed_content_size(self, text: str, icon_size: QSize | None = None) -> QSize:
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

        border = getattr(self, '_text_border', None)
        border_width = float(border.get('width', 0.0) or 0.0) if isinstance(border, dict) else 0.0
        if border_width > 0.0:
            width += border_width
            height += border_width

        shadow = getattr(self, '_text_shadow', None)
        if isinstance(shadow, dict):
            width += abs(float(shadow.get('x', 0.0) or 0.0))
            height += abs(float(shadow.get('y', 0.0) or 0.0))

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
        icon = getattr(self, '_text_icon', None)
        pixmap = icon.get('pixmap') if isinstance(icon, dict) else None
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
        icon = getattr(self, '_text_icon', None)
        size = icon.get('size') if isinstance(icon, dict) else None
        return QSize(size) if isinstance(size, QSize) and size.isValid() else None

    def _text_icon_spacing(self) -> float:
        icon = getattr(self, '_text_icon', None)
        spacing = icon.get('spacing') if isinstance(icon, dict) else 0.0
        try:
            return max(0.0, float(spacing))
        except (TypeError, ValueError):
            return 0.0

    def _text_icon_align(self) -> str:
        icon = getattr(self, '_text_icon', None)
        align = icon.get('align') if isinstance(icon, dict) else 'left'
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
        shadow = getattr(self, '_text_shadow', None)
        if isinstance(shadow, dict):
            shadow_color = shadow.get('color')
            if isinstance(shadow_color, QColor) and shadow_color.isValid() and shadow_color.alpha() > 0:
                offset_rect = rect.translated(float(shadow.get('x', 0.0)), float(shadow.get('y', 0.0)))
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
        shadow = getattr(self, '_text_shadow', None)
        if isinstance(shadow, dict):
            shadow_color = shadow.get('color')
            if isinstance(shadow_color, QColor) and shadow_color.isValid() and shadow_color.alpha() > 0:
                shadow_path = QPainterPath(text_path)
                shadow_path.translate(float(shadow.get('x', 0.0)), float(shadow.get('y', 0.0)))
                painter.fillPath(shadow_path, QBrush(shadow_color))

        border = getattr(self, '_text_border', None)
        if isinstance(border, dict):
            border_color = border.get('color')
            border_width = float(border.get('width', 0.0) or 0.0)
            if isinstance(border_color, QColor) and border_color.isValid() and border_color.alpha() > 0 and border_width > 0.0:
                self._draw_text_outline(
                    painter,
                    text_path,
                    fill=QBrush(text_color),
                    border_color=border_color,
                    border_width=border_width,
                    border_style=border.get('style', 'solid'),
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
        cache = getattr(self, '_text_effect_cache', None)
        if isinstance(cache, dict) and cache.get('key') == key and isinstance(cache.get('path'), QPainterPath):
            return QPainterPath(cache['path'])

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
        cache = getattr(self, '_text_effect_cache', None)
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
            isinstance(cache, dict)
            and cache.get('outline_key') == key
            and isinstance(cache.get('outline'), QPainterPath)
        ):
            return QPainterPath(cache['outline'])

        stroker = QPainterPathStroker()
        stroker.setWidth(max(0.0, float(border_width)))
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setDashPattern(pen_style)

        outline = stroker.createStroke(text_path).subtracted(text_path)
        if not isinstance(cache, dict):
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

    def _handle_overflow_timer_event(self, event) -> bool:
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

    def _draw_faded_text_layer(self, painter: QPainter, rect: QRectF, text: str, draw_layer) -> None:
        width = max(1, int(ceil(rect.width())))
        height = max(1, int(ceil(rect.height())))
        if width <= 1 or height <= 1:
            return

        device_ratio = max(1.0, float(painter.device().devicePixelRatioF()))
        pixmap = QPixmap(max(1, int(width * device_ratio)), max(1, int(height * device_ratio)))
        pixmap.setDevicePixelRatio(device_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        layer_painter = QPainter(pixmap)
        layer_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        layer_painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        layer_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
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


class MTPlainLabel(BoxThemeMixin, _TextEffectMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, *args, obj_name: str = '', **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)

        if obj_name:
            self.setObjectName(obj_name)

    def enterEvent(self, event) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def sizeHint(self) -> QSize:
        base_hint = super().sizeHint()
        if not base_hint.isEmpty() and not self.text() and not self._has_text_icon():
            return base_hint
        if self._has_text_icon():
            return self._themed_visual_content_size(self.text())
        return self._visual_text_size(self.text())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        text_rect = QRectF(self.contentsRect())
        text_overflows = self._text_overflows_rect(self.text(), text_rect)
        if self.has_box_theme() and not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            self.draw_box_theme(painter)
            painter.end()
            super().paintEvent(event)
            return

        if not self.text().strip() and not self._has_text_icon():
            super().paintEvent(event)
            return
        if not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.has_box_theme():
            self.draw_box_theme(painter)
        else:
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

        painter.setFont(self.font())
        self._draw_themed_icon_text(
            painter,
            text_rect,
            self.alignment(),
            self.text(),
            self.palette().windowText().color(),
        )


class MTLabel(BoxThemeMixin, _TextEffectMixin, TranslatableMixin, QLabel):
    PAINTED_BOX_THEME = False

    def __init__(self, *args, tr_key: str, obj_name: str = '', **kwargs) -> None:
        super().__init__(tr_key, *args, **kwargs)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)

        if obj_name:
            self.setObjectName(obj_name)

    def enterEvent(self, event) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event) -> None:
        if self._handle_overflow_timer_event(event):
            return
        super().timerEvent(event)

    def sizeHint(self) -> QSize:
        base_hint = super().sizeHint()
        if not base_hint.isEmpty() and not self.text() and not self._has_text_icon():
            return base_hint
        if self._has_text_icon():
            return self._themed_visual_content_size(self.text())
        return self._visual_text_size(self.text())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        text_rect = QRectF(self.contentsRect())
        text_overflows = self._text_overflows_rect(self.text(), text_rect)
        if self.has_box_theme() and not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            self.draw_box_theme(painter)
            painter.end()
            super().paintEvent(event)
            return

        if not self.text().strip() and not self._has_text_icon():
            super().paintEvent(event)
            return
        if not text_overflows and not self._has_custom_text_render() and not self._has_text_icon():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.has_box_theme():
            self.draw_box_theme(painter)
        else:
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

        painter.setFont(self.font())
        self._draw_themed_icon_text(
            painter,
            text_rect,
            self.alignment(),
            self.text(),
            self.palette().windowText().color(),
        )


class MTButton(BoxThemeMixin, _TextEffectMixin, TranslatableMixin, QPushButton):
    PAINTED_BOX_THEME = False

    def __init__(self, *args, tr_key: str, checkable: bool = False, checked: bool = False, obj_name: str = '', **kwargs) -> None:
        super().__init__(tr_key, *args, **kwargs)
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

    def enterEvent(self, event) -> None:
        self._set_overflow_hover_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_overflow_hover_active(False)
        super().leaveEvent(event)

    def timerEvent(self, event) -> None:
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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.has_box_theme():
            self.draw_box_theme(painter)
        else:
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

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
        if not isinstance(padding, (list, tuple)) or len(padding) != 4:
            return 0.0, 0.0, 0.0, 0.0

        values: list[float] = []
        for value in padding:
            if isinstance(value, bool):
                return 0.0, 0.0, 0.0, 0.0
            if isinstance(value, (int, float)):
                values.append(max(0.0, float(value)))
                continue
            return 0.0, 0.0, 0.0, 0.0
        left, top, right, bottom = values
        return left, top, right, bottom
