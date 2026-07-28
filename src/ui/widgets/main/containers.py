from pathlib import Path
import typing as t

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QDragEnterEvent,
    QDropEvent,
    QEnterEvent,
    QHideEvent,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QRegion,
    QResizeEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.app.paths import PATH_SRC
from src.theme.colors import to_qcolor
from src.utils.conversion import as_dict, as_object_dict, coerce_number
from src.ui.painting import draw_widget_background, new_widget_painter
from src.translation.mixin import TranslatableComboBoxMixin
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets.main.paint_primitives import parse_pen_style, resolve_fill_brush, rounded_rect_path
from src.ui.widgets.main.text import MTButton, MTLabel, MTPlainLabel
from src.ui.widgets.types import WidgetThemeMap

_GROUP_ITEM_INDENT = '   '
_GROUP_SECTION_SPACER_HEIGHT = 8
_DEFAULT_COMBOBOX_ARROW_SOURCE = str(PATH_SRC / 'assets/icons/MTComboBox/arrow_right.svg')


def _draw_aligned_text(
    painter: QPainter,
    rect: QRectF,
    alignment: Qt.AlignmentFlag,
    text: str,
    color: QColor,
) -> None:
    painter.save()
    painter.setPen(color)
    painter.drawText(rect, int(alignment), text)
    painter.restore()


class MTRadioButton(QRadioButton):
    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)


class MTGroupButton(QButtonGroup):
    def __init__(
        self,
        *,
        obj_name: str = '',
        exclusive: bool = True,
    ) -> None:
        super().__init__()
        self.setExclusive(exclusive)

        if obj_name:
            self.setObjectName(obj_name)


class _MTComboPopupItem(MTButton):
    def __init__(self, combo_box: 'MTComboBox', index: int, parent: QWidget | None = None) -> None:
        super().__init__(tr_key='', checkable=True, obj_name=combo_box.popup_item_object_name(index), parent=parent)
        self._combo_box = combo_box
        self._index = index
        self.setText(combo_box.itemText(index))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self, _checked: bool = False) -> None:
        self._combo_box.activate_popup_item(self._index)

    def sync_from_combo(self) -> None:
        self.setText(self._combo_box.itemText(self._index))
        self.setChecked(self._combo_box.currentIndex() == self._index)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(max(1, self._combo_box.popup_target_width()), self._combo_box.popup_item_height())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = new_widget_painter(self, text_antialias=True, smooth_pixmap=True)
        state = 'selected' if self.isChecked() else 'hover' if self.underMouse() else None
        rect = QRectF(self.rect())
        self._combo_box.draw_popup_item_background(painter, rect, state)
        self._combo_box.draw_popup_item_text(painter, rect, state, self.text())
        painter.end()


class _MTComboPopup(QFrame):
    def __init__(self, combo_box: 'MTComboBox') -> None:
        super().__init__(
            combo_box,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint,
        )
        self._combo_box = combo_box
        self.setObjectName(combo_box.popup_object_name())
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setGraphicsEffect(t.cast(t.Any, None))
        self._layout = create_layout(LayoutType.VBOX, parent=self)
        self._items: list[_MTComboPopupItem] = []
        self._dirty = True

    def rebuild(self) -> None:
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

        for index in range(self._combo_box.count()):
            item = _MTComboPopupItem(self._combo_box, index, parent=self)
            self._items.append(item)
            self._layout.addWidget(item)
        self.sync_items()
        self._dirty = False

    def mark_dirty(self) -> None:
        self._dirty = True

    def sync_items(self) -> None:
        for item in self._items:
            item.sync_from_combo()

    def show_for_combo(self) -> None:
        if self._dirty:
            self.rebuild()
        else:
            self.sync_items()
        self._combo_box.sync_popup_geometry()
        self.show()
        self.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.apply_shape_mask()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = new_widget_painter(self)
        self._combo_box.draw_popup_background(painter, QRectF(self.rect()))
        painter.end()

    def hideEvent(self, event: QHideEvent) -> None:
        self._combo_box.on_popup_hidden()
        super().hideEvent(event)

    def apply_shape_mask(self) -> None:
        rect = QRectF(self.rect())
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            self.clearMask()
            return

        popup_part = self._combo_box.combo_parts().get('popup')
        popup_part_map = as_dict(popup_part) or {}
        radius = self._combo_box.resolve_radius(
            popup_part_map.get('border_radius'),
            rect,
        )
        if radius <= 0.0:
            self.clearMask()
            return

        path = self._combo_box.rounded_path(rect, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class MTComboBox(TranslatableComboBoxMixin, QWidget):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)
    activated = Signal(int)
    popupOpened = Signal()
    popupClosed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
    ) -> None:
        self._items: list[dict[str, t.Any]] = []
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._current_index = -1
        self._parts: dict[str, WidgetThemeMap] = self._build_default_parts()
        self._alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self._content_width_mode = 'longest'
        self._content_width_floor = 0
        self._popup_hide_expected = False
        self._suppress_next_mouse_press = False
        self._popup_close_notified = False
        self._popup_hide_timer = QTimer(self, singleShot=True)
        self._popup_hide_timer.timeout.connect(self._finalize_popup_hide)

        if obj_name:
            self.setObjectName(obj_name)

        self._popup = _MTComboPopup(self)

    def sizeHint(self) -> QSize:
        text = self.currentText()
        text_width = self.fontMetrics().horizontalAdvance(text) if text else 1
        return QSize(
            max(1, text_width + int(round(self._button_width()))),
            max(1, self.fontMetrics().height()),
        )

    def minimumSizeHint(self) -> QSize:
        text = self.currentText()
        text_width = self.fontMetrics().horizontalAdvance(text) if text else 1
        return QSize(
            max(1, text_width + int(round(self._button_width()))),
            max(1, self.fontMetrics().height()),
        )

    def addItem(self, text: str, userData: object = None) -> None:
        data = {
            'text': str(text),
            'roles': {
                int(Qt.ItemDataRole.UserRole): userData,
            },
        }
        self._items.append(data)
        if self._current_index < 0:
            self.setCurrentIndex(0)
        self._popup.mark_dirty()
        self.update()

    def addItems(self, texts: list[str]) -> None:
        for text in texts:
            self.addItem(text)

    def clear(self) -> None:
        had_current = self._current_index
        self._items.clear()
        self._current_index = -1
        self._popup.mark_dirty()
        self.update()
        if had_current != -1:
            self.currentIndexChanged.emit(-1)
            self.currentTextChanged.emit('')

    def count(self) -> int:
        return len(self._items)

    def currentIndex(self) -> int:
        return self._current_index

    def currentText(self) -> str:
        return self.itemText(self._current_index)

    def setCurrentIndex(self, index: int) -> None:
        index = int(index)
        if index < 0 or index >= self.count():
            index = -1
        if index == self._current_index:
            self._popup.sync_items()
            return
        self._current_index = index
        self._popup.sync_items()
        self.update()
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(self.currentText())

    def setCurrentText(self, text: str) -> None:
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)

    def itemText(self, index: int) -> str:
        if 0 <= index < self.count():
            return str(self._items[index].get('text', ''))
        return ''

    def setItemText(self, index: int, text: str) -> None:
        if not 0 <= index < self.count():
            return
        self._items[index]['text'] = str(text)
        self._popup.sync_items()
        self.update()

    def itemData(self, index: int, role: int = Qt.ItemDataRole.UserRole) -> object:
        if not 0 <= index < self.count():
            return None
        roles = as_object_dict(self._items[index].get('roles'))
        if roles is None:
            return None
        return roles.get(int(role))

    def setItemData(self, index: int, value: object, role: int = Qt.ItemDataRole.UserRole) -> None:
        if not 0 <= index < self.count():
            return
        roles = self._items[index].setdefault('roles', {})
        if isinstance(roles, dict):
            roles[int(role)] = value

    def findData(self, value: object, role: int = Qt.ItemDataRole.UserRole) -> int:
        for index in range(self.count()):
            if self.itemData(index, role) == value:
                return index
        return -1

    def findText(self, text: str) -> int:
        needle = str(text)
        for index in range(self.count()):
            if self.itemText(index) == needle:
                return index
        return -1

    def showPopup(self) -> None:
        if self.count() <= 0 or self._popup.isVisible():
            return
        if self._popup_hide_timer.isActive():
            self._popup_hide_timer.stop()
        self._popup_close_notified = False
        self._suppress_next_mouse_press = False
        self.popupOpened.emit()
        self._popup.show_for_combo()

    def hidePopup(self) -> None:
        if not self._popup.isVisible():
            return
        if self._popup_hide_timer.isActive():
            return

        close_delay = max(0, int(round(coerce_number(self.property('_themePopupCloseDelayMs')) or 0.0)))
        self._popup_close_notified = True
        self.popupClosed.emit()
        if close_delay > 0:
            self._popup_hide_timer.start(close_delay)
            return
        self._finalize_popup_hide()

    def view(self) -> QWidget:
        return self._popup

    def setAlignment(self, alignment: Qt.AlignmentFlag) -> None:
        self._alignment = alignment
        self.update()

    def alignment(self) -> Qt.AlignmentFlag:
        return self._alignment


    def set_content_width_mode(self, mode: str) -> None:
        normalized = str(mode or 'longest').strip().lower()
        if normalized not in {'none', 'current', 'longest'}:
            normalized = 'longest'
        if normalized == self._content_width_mode:
            return
        self._content_width_mode = normalized
        if normalized == 'none':
            self.setMinimumWidth(max(self._content_width_floor, int(round(self._button_width()))))

    def content_width_mode(self) -> str:
        return self._content_width_mode

    def popup_object_name(self) -> str:
        base_name = self.objectName().strip() or type(self).__name__
        return f'{base_name}_Popup'

    def popup_item_object_name(self, index: int) -> str:
        base_name = self.objectName().strip() or type(self).__name__
        return f'{base_name}_Popup_Item_{index}'

    def combo_parts(self) -> dict[str, WidgetThemeMap]:
        return self._parts

    def _build_default_parts(self) -> dict[str, WidgetThemeMap]:
        transparent = QColor(Qt.GlobalColor.transparent)
        return {
            'button': {
                'background_color': QColor(transparent),
                'border_color': QColor(transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'width': 18.0,
            },
            'icon': {
                'color': QColor('#000'),
                'size': 18.0,
                'rotation': 0.0,
                'source': _DEFAULT_COMBOBOX_ARROW_SOURCE,
            },
            'popup': {
                'background_color': QColor(Qt.GlobalColor.white),
                'border_color': QColor(Qt.GlobalColor.transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'width': None,
                'height': None,
            },
            'item': {
                'background_color': QColor(Qt.GlobalColor.transparent),
                'text_color': QColor(),
                'border_color': QColor(Qt.GlobalColor.transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'height': None,
                'padding': (0.0, 0.0, 0.0, 0.0),
                'states': {
                    'hover': {
                        'background_color': QColor(),
                        'text_color': QColor(),
                        'border_color': QColor(),
                    },
                    'selected': {
                        'background_color': QColor(),
                        'text_color': QColor(),
                        'border_color': QColor(),
                    },
                },
            },
        }

    def _part_data(self, part: str) -> WidgetThemeMap:
        return self._parts.setdefault(part, {})

    def _existing_part_data(self, part: str) -> WidgetThemeMap | None:
        return self._parts.get(part)

    def current_part_color(self, part: str, css_name: str = 'background-color') -> QColor:
        if part == 'item' and css_name.startswith('states.'):
            path = css_name.split('.')
            state_map = as_dict(self._part_data('item').get('states'))
            state = as_dict(None if state_map is None else state_map.get(path[1])) if len(path) == 3 and path[0] == 'states' else None
            if state is not None:
                key = {
                    'background-color': 'background_color',
                    'color': 'text_color',
                    'border-color': 'border_color',
                }.get(path[2])
                color = state.get(key) if key is not None else None
                return QColor(color) if isinstance(color, QColor) and color.isValid() else QColor()
            return QColor()

        data = self._existing_part_data(part)
        if data is None:
            return QColor()

        if css_name == 'border-color':
            color = data.get('border_color')
        elif css_name == 'color':
            color = data.get('color') if part == 'icon' else data.get('text_color', data.get('background_color'))
        else:
            color = data.get('background_color')
        if isinstance(color, QColor) and color.isValid():
            return QColor(color)
        return QColor()

    def set_part_color(self, part: str, value: object, css_name: str = 'background-color') -> bool:
        color = to_qcolor(value)
        data = self._existing_part_data(part)
        if color is None or data is None:
            return False

        if css_name == 'border-color':
            data['border_color'] = QColor(color)
        elif css_name == 'color':
            if part == 'icon':
                data['color'] = QColor(color)
            elif 'text_color' in data:
                data['text_color'] = QColor(color)
            else:
                data['background_color'] = QColor(color)
        else:
            data['background_color'] = QColor(color)
        self._refresh_part(part)
        return True

    def set_part_style_value(self, part: str, path: tuple[str, ...], value: object) -> bool:
        if part == 'item' and len(path) >= 3 and path[0] == 'states':
            return self._set_item_state_style_value(path[1], path[2:], value)
        if path == ('color',):
            return self.set_part_color(part, value, 'color')
        if path == ('background', 'color'):
            return self.set_part_color(part, value, 'background-color')
        if path == ('border', 'color'):
            return self.set_part_color(part, value, 'border-color')
        if path == ('text', 'color'):
            return self.set_part_color(part, value, 'color')
        if part == 'icon' and path in {('source',), ('path',), ('file',)}:
            data = self._existing_part_data(part)
            if data is None:
                return False
            data['source'] = str(value).strip()
            self._refresh_part(part)
            return True
        if path == ('border', 'width'):
            return self.set_part_metric(part, ('border', 'width'), coerce_number(value) or 0.0)
        if path == ('border', 'radius'):
            data = self._existing_part_data(part)
            if data is None or 'border_radius' not in data:
                return False
            data['border_radius'] = value
            self._refresh_part(part)
            return True
        return False

    def _set_item_state_style_value(self, state_name: str, path: tuple[str, ...], value: object) -> bool:
        state_map = as_dict(self._part_data('item').get('states'))
        state = as_dict(None if state_map is None else state_map.get(state_name))
        if state is None:
            return False

        if path == ('background', 'color'):
            color = to_qcolor(value)
            if color is None:
                return False
            state['background_color'] = QColor(color)
        elif path in {('text', 'color'), ('color',)}:
            color = to_qcolor(value)
            if color is None:
                return False
            state['text_color'] = QColor(color)
        elif path == ('border', 'color'):
            color = to_qcolor(value)
            if color is None:
                return False
            state['border_color'] = QColor(color)
        else:
            return False

        self._refresh_part('item')
        return True

    def current_part_metric(self, part: str, metric_path: tuple[str, ...], fallback: float = 0.0) -> float:
        data = self._existing_part_data(part)
        if data is None:
            return float(fallback)
        part_key = str(part).strip()
        normalized_path = tuple(metric_path)
        if part_key == 'popup' and normalized_path == ('width',):
            return float(self.popup_target_width())
        if part_key == 'popup' and normalized_path == ('height',):
            return float(self.popup_target_height())
        if normalized_path == ('border', 'width'):
            data_key = 'border_width'
        elif normalized_path == ('border', 'radius'):
            data_key = 'border_radius'
        elif normalized_path == ('width',):
            data_key = 'width'
        elif normalized_path == ('size',):
            data_key = 'size'
        elif normalized_path == ('rotation',):
            data_key = 'rotation'
        elif normalized_path == ('height',):
            data_key = 'height'
        else:
            return float(fallback)
        metric_value = coerce_number(data.get(data_key))
        if normalized_path == ('border', 'radius'):
            return float(metric_value if metric_value is not None else fallback)
        if metric_value is not None:
            return float(metric_value)
        return float(fallback)

    def set_part_metric(self, part: str, metric_path: tuple[str, ...] | str, value: float) -> bool:
        data = self._existing_part_data(part)
        if data is None:
            return False
        if isinstance(metric_path, str):
            metric_path = (metric_path,)
        part_key = str(part).strip()
        normalized_path = tuple(metric_path)

        if normalized_path == ('border', 'width') and 'border_width' in data:
            data['border_width'] = max(0.0, float(value))
            self._refresh_part(part_key)
            return True
        if normalized_path == ('border', 'radius') and 'border_radius' in data:
            data['border_radius'] = max(0.0, float(value))
            self._refresh_part(part_key)
            return True

        metric_value = float(value)
        if part_key == 'button' and normalized_path == ('width',):
            data['width'] = max(0.0, metric_value)
        elif part_key == 'popup' and normalized_path == ('width',):
            data['width'] = max(0.0, metric_value)
        elif part_key == 'popup' and normalized_path == ('height',):
            data['height'] = max(0.0, metric_value)
        elif part_key == 'icon' and normalized_path == ('size',):
            data['size'] = max(0.0, metric_value)
        elif part_key == 'icon' and normalized_path == ('rotation',):
            data['rotation'] = metric_value
        elif part_key == 'item' and normalized_path == ('height',):
            data['height'] = max(1.0, metric_value)
        else:
            return False
        self._refresh_part(part_key)
        return True

    def _refresh_part(self, part: str) -> None:
        if part in {'popup', 'item'}:
            self._sync_popup_view()
            try:
                self.sync_popup_geometry()
                self._popup.update()
                self._popup.sync_items()
            except RuntimeError:
                pass
        self.update()
        self.updateGeometry()

    def _sync_popup_view(self) -> None:
        try:
            self._popup.apply_shape_mask()
            self._popup.update()
            self._popup.sync_items()
        except RuntimeError:
            return

    def popup_item_height(self) -> int:
        height = self._part_data('item').get('height')
        if isinstance(height, (int, float)) and float(height) > 0:
            return int(round(float(height)))
        return max(1, self.fontMetrics().height())

    def popup_target_width(self) -> int:
        requested = coerce_number(self._part_data('popup').get('width'))
        if requested is not None:
            return max(0, int(round(requested)))
        return max(1, self.width())

    def popup_target_height(self) -> int:
        requested = coerce_number(self._part_data('popup').get('height'))
        content_height = max(0, self.count() * self.popup_item_height())
        if requested is not None:
            if content_height > 0:
                return max(0, min(int(round(requested)), content_height))
            return max(0, int(round(requested)))
        return max(1, content_height)

    def sync_popup_geometry(self) -> None:
        try:
            self._popup.isVisible()
        except RuntimeError:
            return

        width = max(1, self.popup_target_width())
        height = max(1, self.popup_target_height())
        self._popup.setFixedWidth(width)
        self._popup.setFixedHeight(height)
        self._popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self._popup.apply_shape_mask()

    def draw_popup_item_background(self, painter: QPainter, rect: QRectF, state_name: str | None) -> None:
        item_part = self._part_data('item')
        state_map = as_dict(self._part_data('item').get('states'))
        state = as_dict(None if state_map is None or state_name is None else state_map.get(state_name))
        color = state.get('background_color') if state is not None else None
        border_color = state.get('border_color') if state is not None else None
        if not (isinstance(color, QColor) and color.isValid()):
            color = item_part.get('background_color')
        if not (isinstance(border_color, QColor) and border_color.isValid()):
            border_color = item_part.get('border_color')
        border_width = float(coerce_number(item_part.get('border_width')) or 0.0)
        border_style = parse_pen_style(item_part.get('border_style', 'solid'))
        radius = self.resolve_radius(item_part.get('border_radius'), rect)

        painter.save()
        painter.setBrush(
            resolve_fill_brush(
                rect,
                color=color if isinstance(color, QColor) and color.isValid() else None,
            )
        )

        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        painter.drawPath(self.rounded_path(draw_rect, radius))
        painter.restore()

    def draw_popup_background(self, painter: QPainter, rect: QRectF) -> None:
        popup = self._part_data('popup')
        border_width = float(coerce_number(popup.get('border_width')) or 0.0)
        border_color = popup.get('border_color')
        border_style = parse_pen_style(popup.get('border_style', 'solid'))

        painter.save()
        background = popup.get('background_color')
        painter.setBrush(
            resolve_fill_brush(
                rect,
                color=background if isinstance(background, QColor) and background.isValid() else None,
            )
        )

        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        radius = self.resolve_radius(popup.get('border_radius'), draw_rect)
        painter.drawPath(self.rounded_path(draw_rect, radius))
        painter.restore()

    def draw_popup_item_text(self, painter: QPainter, rect: QRectF, state_name: str | None, text: str) -> None:
        state_map = as_dict(self._part_data('item').get('states'))
        state = as_dict(None if state_map is None or state_name is None else state_map.get(state_name))
        color = state.get('text_color') if state is not None else None
        if not (isinstance(color, QColor) and color.isValid()):
            color = self._part_data('item').get('text_color')
        if not isinstance(color, QColor) or not color.isValid():
            color = self.palette().color(self.foregroundRole())

        painter.save()
        painter.setFont(self.font())
        padding = t.cast(tuple[object, object, object, object], self._part_data('item').get('padding', (0.0, 0.0, 0.0, 0.0)))
        top, right, bottom, left = padding
        text_rect = rect.adjusted(
            float(coerce_number(left) or 0.0),
            float(coerce_number(top) or 0.0),
            -float(coerce_number(right) or 0.0),
            -float(coerce_number(bottom) or 0.0),
        )
        _draw_aligned_text(
            painter,
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
            color,
        )
        painter.restore()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = new_widget_painter(self, text_antialias=True, smooth_pixmap=True)

        draw_widget_background(self, painter)

        button_rect = self._button_rect()
        self._draw_button_part(painter, button_rect)
        self._draw_current_text(painter, button_rect)
        self._draw_arrow_part(painter, button_rect)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._suppress_next_mouse_press:
                self._suppress_next_mouse_press = False
                event.accept()
                return
            if self._popup.isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Down}:
            self.showPopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._popup.isVisible():
            self.sync_popup_geometry()
            self._popup.raise_()

    def activate_popup_item(self, index: int) -> None:
        self.setCurrentIndex(index)
        self.activated.emit(index)
        self.hidePopup()

    def on_popup_hidden(self) -> None:
        close_notified = self._popup_close_notified
        self._popup_close_notified = False
        if self._popup_hide_expected:
            self._popup_hide_expected = False
        else:
            self._suppress_next_mouse_press = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if not close_notified:
            self.popupClosed.emit()

    def _finalize_popup_hide(self) -> None:
        if not self._popup.isVisible():
            self._popup_close_notified = False
            return
        self._popup_hide_expected = True
        self._popup.hide()

    def _draw_current_text(self, painter: QPainter, button_rect: QRectF) -> None:
        rect = QRectF(self.contentsRect())
        text_rect = rect.adjusted(0.0, 0.0, -button_rect.width(), 0.0)
        if not text_rect.isValid():
            return

        text = self.fontMetrics().elidedText(
            self.currentText(),
            Qt.TextElideMode.ElideRight,
            max(0, int(text_rect.width())),
        )
        painter.save()
        painter.setFont(self.font())
        _draw_aligned_text(
            painter,
            text_rect,
            self._alignment,
            text,
            self.palette().color(self.foregroundRole()),
        )
        painter.restore()

    def _draw_button_part(self, painter: QPainter, rect: QRectF) -> None:
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
            return

        painter.save()
        button_part = self._part_data('button')
        background_color = button_part.get('background_color')
        painter.setBrush(
            resolve_fill_brush(
                rect,
                color=background_color if isinstance(background_color, QColor) and background_color.isValid() else None,
            )
        )

        border_width = float(coerce_number(button_part.get('border_width')) or 0.0)
        border_color = button_part.get('border_color')
        border_style = parse_pen_style(button_part.get('border_style', 'solid'))
        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        radius = self.resolve_radius(button_part.get('border_radius'), draw_rect)
        painter.drawPath(self.rounded_path(draw_rect, radius))
        painter.restore()

    def _draw_arrow_part(self, painter: QPainter, button_rect: QRectF) -> None:
        icon_part = self._part_data('icon')
        size = coerce_number(icon_part.get('size')) or 0.0
        if size <= 0 or not button_rect.isValid():
            return

        color = icon_part.get('color')
        if not isinstance(color, QColor) or not color.isValid():
            color = self.palette().color(self.foregroundRole())
        rotation = float(coerce_number(icon_part.get('rotation')) or 0.0)

        source = str(icon_part.get('source') or '').strip()
        if source:
            icon = QIcon(source)
            if not icon.isNull():
                icon_size = max(1, int(round(size)))
                pixmap = icon.pixmap(icon_size, icon_size)
                if not pixmap.isNull():
                    if color.isValid() and color.alpha() > 0:
                        tinted = QPixmap(pixmap.size())
                        tinted.fill(Qt.GlobalColor.transparent)
                        tint_painter = QPainter(tinted)
                        tint_painter.drawPixmap(0, 0, pixmap)
                        tint_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        tint_painter.fillRect(tinted.rect(), color)
                        tint_painter.end()
                        pixmap = tinted

                    target = QRectF(
                        button_rect.center().x() - (icon_size / 2.0),
                        button_rect.center().y() - (icon_size / 2.0),
                        float(icon_size),
                        float(icon_size),
                    )
                    painter.save()
                    if abs(rotation) > 0.001:
                        painter.translate(target.center())
                        painter.rotate(rotation)
                        painter.translate(-target.center())
                    painter.drawPixmap(target.toRect(), pixmap)
                    painter.restore()
                    return

        center = button_rect.center()
        half = size / 2.0
        path = QPainterPath()
        path.moveTo(QPointF(center.x() - half, center.y() - (half / 2.0)))
        path.lineTo(QPointF(center.x() + half, center.y() - (half / 2.0)))
        path.lineTo(QPointF(center.x(), center.y() + half))
        path.closeSubpath()

        painter.save()
        if abs(rotation) > 0.001:
            painter.translate(center)
            painter.rotate(rotation)
            painter.translate(-center)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)
        painter.restore()

    def _button_rect(self) -> QRectF:
        rect = QRectF(self.contentsRect())
        width = min(rect.width(), self._button_width())
        return QRectF(rect.right() - width + 1.0, rect.top(), width, rect.height())

    def _button_width(self) -> float:
        return max(0.0, coerce_number(self._part_data('button').get('width')) or 0.0)

    def resolve_radius(self, value: object, rect: QRectF) -> float:
        base = max(0.0, min(rect.width(), rect.height()) / 2.0)
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), base))
        if isinstance(value, str):
            text = value.strip().lower()
            if text.endswith('%'):
                try:
                    return max(0.0, min((min(rect.width(), rect.height()) * float(text[:-1].strip())) / 100.0, base))
                except ValueError:
                    return 0.0
            if text.endswith('px'):
                text = text[:-2].strip()
            try:
                return max(0.0, min(float(text), base))
            except ValueError:
                return 0.0
        return 0.0

    def rounded_path(self, rect: QRectF, radius: float) -> QPainterPath:
        return rounded_rect_path(rect, radius)

class MTScrollArea(QScrollArea):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(20)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setStyleSheet('background: transparent; border: 0;')

        if obj_name:
            self.setObjectName(obj_name)

class MTWidget(QWidget):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name:
            self.setObjectName(obj_name)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = new_widget_painter(self, antialias=False)
        draw_widget_background(self, painter)
        painter.end()
        super().paintEvent(event)


class _MTListItem(MTButton):
    def __init__(
        self,
        *,
        text: str,
        value: str,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr_key='', checkable=True, obj_name=obj_name, parent=parent)
        self._value = str(value)
        self.setText(str(text))
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(1, max(1, hint.height()))

    def data(self, role: int) -> str | None:
        if role == Qt.ItemDataRole.UserRole:
            return self._value
        if role == Qt.ItemDataRole.DisplayRole:
            return self.text()
        return None


class MTListWidget(MTScrollArea):
    currentItemChanged = Signal(object, object)
    itemPressed = Signal(object)
    itemClicked = Signal(object)

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent, obj_name=obj_name)
        self._content = MTWidget(obj_name=f'{obj_name}_Content' if obj_name else '')
        self._content_layout = create_layout(LayoutType.VBOX, parent=self._content)
        self.setWidget(self._content)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._items: list[QWidget] = []
        self._current_item: _MTListItem | None = None

    def clear(self) -> None:
        previous = self._current_item
        self._current_item = None
        for item in self._items:
            self._content_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        if previous is not None:
            self.currentItemChanged.emit(None, previous)

    def add_item(self, text: str, value: str, *, obj_name: str = '') -> _MTListItem:
        item = _MTListItem(
            text=text,
            value=value,
            obj_name=obj_name or self._item_object_name(value),
            parent=self._content,
        )
        def emit_pressed() -> None:
            self.itemPressed.emit(item)

        def handle_clicked(_checked: bool = False) -> None:
            self._activate_item(item)

        item.pressed.connect(emit_pressed)
        item.clicked.connect(handle_clicked)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def add_header(self, text: str, *, obj_name: str = '') -> MTPlainLabel:
        item = MTPlainLabel(str(text), obj_name=obj_name or self._item_object_name(text, suffix='Header'), parent=self._content)
        item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def add_spacer(self, height: int = _GROUP_SECTION_SPACER_HEIGHT) -> MTWidget:
        item = MTWidget(parent=self._content)
        item.setFixedHeight(max(0, int(height)))
        item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._items.append(item)
        self._content_layout.addWidget(item)
        return item

    def count(self) -> int:
        return len(self._items)

    def item(self, index: int) -> QWidget | None:
        if 0 <= int(index) < len(self._items):
            return self._items[int(index)]
        return None

    def row(self, item: QWidget | None) -> int:
        if item is None:
            return -1
        try:
            return self._items.index(item)
        except ValueError:
            return -1

    def currentItem(self) -> _MTListItem | None:
        return self._current_item

    def setCurrentItem(self, item: _MTListItem | None) -> None:
        if item is not None and item not in self._items:
            item = None
        if self._current_item is item:
            if item is not None and not item.isChecked():
                item.setChecked(True)
            return

        previous = self._current_item
        if previous is not None:
            previous.setChecked(False)
        self._current_item = item
        if item is not None:
            item.setChecked(True)
        self.currentItemChanged.emit(item, previous)

    def setCurrentRow(self, index: int) -> None:
        item = self.item(index)
        self.setCurrentItem(item if isinstance(item, _MTListItem) else None)

    def setCurrentValue(self, value: str | None) -> None:
        if value is None:
            self.setCurrentItem(None)
            return
        for item in self._items:
            if isinstance(item, _MTListItem) and item.data(Qt.ItemDataRole.UserRole) == value:
                self.setCurrentItem(item)
                return
        self.setCurrentItem(None)

    def _activate_item(self, item: _MTListItem) -> None:
        self.setCurrentItem(item)
        self.itemClicked.emit(item)

    def _item_object_name(self, value: str, *, suffix: str = 'Item') -> str:
        base = self.objectName().strip() or type(self).__name__
        token = ''.join(char if char.isalnum() else '_' for char in str(value).strip())
        token = '_'.join(part for part in token.split('_') if part) or 'Empty'
        return f'{base}_{suffix}_{token}'


class MTLabeledList(MTWidget):
    def __init__(
        self,
        *,
        obj_name: str = '',
        list_obj_name: str = '',
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, obj_name=obj_name if obj_name else '')

        layout = create_layout(LayoutType.VBOX, parent=self)

        self.list_widget = MTListWidget(self, obj_name=list_obj_name)
        layout.addWidget(self.list_widget)

    def set_items(self, items: t.Sequence[str], *, preferred: str | None = None) -> bool:
        target = preferred if preferred in items else items[0] if items else None
        if self._plain_values() == [str(item) for item in items]:
            self.list_widget.setCurrentValue(target)
            return False

        self.list_widget.clear()
        for name in items:
            self.list_widget.add_item(name, name)
        self.list_widget.setCurrentValue(target)
        return True

    def set_grouped_items(self, groups: t.Sequence[tuple[str, t.Sequence[tuple[str, str]]]], *, preferred: str | None = None) -> None:
        available_values = [
            value
            for _, items in groups
            for _, value in items
        ]
        target = preferred if preferred in available_values else (available_values[0] if available_values else None)

        self.list_widget.clear()
        is_first_group = True
        for group_label, group_items in groups:
            if group_label.strip():
                if not is_first_group and self.list_widget.count() > 0:
                    self.list_widget.add_spacer()
                self.list_widget.add_header(group_label)

            for display_text, value in group_items:
                self.list_widget.add_item(f'{_GROUP_ITEM_INDENT}{display_text}', value)

            is_first_group = False

        self.list_widget.setCurrentValue(target)

    def current_value(self) -> str | None:
        item = self.list_widget.currentItem()
        if not isinstance(item, _MTListItem):
            return None

        value = item.data(Qt.ItemDataRole.UserRole)
        return value.strip() if isinstance(value, str) else None

    def _plain_values(self) -> list[str]:
        values: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if not isinstance(item, _MTListItem):
                return []

            value = item.data(Qt.ItemDataRole.UserRole)
            values.append(str(value) if value is not None else '')

        return values


class MTDropZone(MTWidget):
    files_dropped = Signal(list)
    text_dropped = Signal(str)

    def __init__(
        self,
        *,
        accept_files: bool = True,
        accept_text: bool = True,
        tr_key: str = '',
        obj_name: str = '',
    ) -> None:
        super().__init__(obj_name=f'{obj_name}_Drop_Zone' if obj_name else '')

        self._accept_files = bool(accept_files)
        self._accept_text = bool(accept_text)

        self.setAcceptDrops(self._accept_files or self._accept_text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if self._accept_files:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = create_layout(LayoutType.VBOX, parent=self)

        self._title_label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Drop_Zone_Title' if obj_name else '')
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title_label)

        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._paste_shortcut.activated.connect(self._on_paste_shortcut)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._can_accept_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._process_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            if self._accept_files:
                self._browse_files()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def _on_paste_shortcut(self) -> None:
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        self._process_mime(mime)

    def _browse_files(self) -> None:
        caption = self._title_label.text().strip() or 'Select files'
        start_dir = str(Path.home())
        selected_paths, _ = QFileDialog.getOpenFileNames(self, caption, start_dir)
        if not selected_paths:
            return

        paths = [path for path in (Path(item) for item in selected_paths) if path.exists()]
        if not paths:
            return
        self.files_dropped.emit(paths)

    def _can_accept_mime(self, mime: QMimeData | None) -> bool:
        if mime is None:
            return False

        if self._accept_files:
            if mime.hasUrls():
                return True
            if mime.hasText() and bool(self._extract_paths_from_text(mime.text())):
                return True

        if self._accept_text and mime.hasText() and bool(mime.text().strip()):
            return True

        return False

    def _process_mime(self, mime: QMimeData | None) -> bool:
        if mime is None:
            return False

        accepted = False
        dropped_paths: list[Path] = []

        if self._accept_files:
            dropped_paths = self._extract_paths(mime)
            if dropped_paths:
                self.files_dropped.emit(dropped_paths)
                accepted = True

        if self._accept_text and mime.hasText():
            text = mime.text().strip()
            skip_as_text = self._accept_files and (
                self._looks_like_uri_dump(text) or self._looks_like_paths_dump(text)
            )
            if text and not skip_as_text:
                self.text_dropped.emit(text)
                accepted = True

        return accepted

    def _extract_paths(self, mime: QMimeData) -> list[Path]:
        urls_paths = self._extract_paths_from_urls(mime)
        if urls_paths:
            return urls_paths

        if mime.hasText():
            return self._extract_paths_from_text(mime.text())

        return []

    def _extract_paths_from_urls(self, mime: QMimeData) -> list[Path]:
        paths: list[Path] = []
        seen: set[str] = set()

        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if not path.exists():
                continue

            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)

        return paths

    def _extract_paths_from_text(self, text: str) -> list[Path]:
        paths: list[Path] = []
        seen: set[str] = set()

        for line in text.splitlines():
            path = self._line_to_existing_path(line)
            if path is None:
                continue

            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)

        return paths

    def _line_to_existing_path(self, line: str) -> Path | None:
        candidate = line.strip().strip('"')
        if not candidate:
            return

        path: Path | None = None
        if candidate.lower().startswith('file://'):
            url = QUrl(candidate)
            if url.isLocalFile():
                path = Path(url.toLocalFile())
        else:
            path = Path(candidate)

        if path is None or not path.exists():
            return
        return path

    def _looks_like_uri_dump(self, text: str) -> bool:
        lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        return all(line.startswith('file://') for line in lines)

    def _looks_like_paths_dump(self, text: str) -> bool:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        return all(self._line_to_existing_path(line) is not None for line in lines)

    def _path_key(self, path: Path) -> str:
        try:
            return str(path.resolve()).lower()
        except OSError:
            return str(path.absolute()).lower()
