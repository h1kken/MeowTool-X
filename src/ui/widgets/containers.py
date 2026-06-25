from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence, cast

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
    QFileDialog,
    QFrame,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.app.paths import PATH_SRC
from src.theme.colors import to_qcolor
from src.theme.gradients import build_background_brush, normalize_gradient_data
from src.theme.schema.access import coerce_box_sides, coerce_number, object_map, theme_map
from src.ui.painting import draw_widget_background, new_widget_painter
from src.translation.mixin import TranslatableComboBoxMixin
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets.box import BoxThemeMixin
from src.ui.widgets.text import MTButton, MTLabel, MTPlainLabel, TextEffectMixin
from src.ui.widgets.types import WidgetThemeMap

_GROUP_ITEM_INDENT = '   '
_GROUP_SECTION_SPACER_HEIGHT = 8
_DEFAULT_COMBOBOX_ARROW_SOURCE = str(PATH_SRC / 'assets/icons/MTComboBox/arrow_right.svg')
print(_DEFAULT_COMBOBOX_ARROW_SOURCE)
input()


class MTRadioButton(BoxThemeMixin, QRadioButton):
    PAINTED_BOX_THEME = False

    def __init__(self, text: str = '', parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(text, parent)
        self.init_box_theme()

        if obj_name:
            self.setObjectName(obj_name)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.has_box_theme():
            painter = new_widget_painter(self)
            self.draw_box_theme(painter)
            painter.end()
        super().paintEvent(event)


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


class _MTComboPopup(BoxThemeMixin, QFrame):
    PAINTED_BOX_THEME = False

    def __init__(self, combo_box: 'MTComboBox') -> None:
        super().__init__(
            combo_box,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint,
        )
        self._combo_box = combo_box
        self.init_box_theme()
        self.setObjectName(combo_box.popup_object_name())
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setGraphicsEffect(cast(Any, None))
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

        popup_theme = self._combo_box.combo_parts().get('popup')
        popup_theme_map = theme_map(popup_theme) or {}
        radius = self._combo_box.resolve_radius(
            popup_theme_map.get('border_radius'),
            rect,
        )
        if radius <= 0.0:
            self.clearMask()
            return

        path = self._combo_box.rounded_path(rect, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class MTComboBox(BoxThemeMixin, TextEffectMixin, TranslatableComboBoxMixin, QWidget):
    PAINTED_BOX_THEME = False

    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)
    activated = Signal(int)
    popupOpened = Signal()
    popupClosed = Signal()

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.init_box_theme()
        self.init_text_effects()
        self.set_force_text_path_render(True)
        self._items: list[dict[str, Any]] = []
        self._current_index = -1
        self._default_parts: dict[str, WidgetThemeMap] = self._build_default_parts()
        self._parts: dict[str, WidgetThemeMap] = deepcopy(self._default_parts)
        self._alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self._content_width_mode = 'longest'
        self._content_width_floor = 0
        self._popup_hide_expected = False
        self._suppress_next_mouse_press = False
        self._popup_close_notified = False
        self._popup_hide_timer = QTimer(self)
        self._popup_hide_timer.setSingleShot(True)
        self._popup_hide_timer.timeout.connect(self._finalize_popup_hide)

        if obj_name:
            self.setObjectName(obj_name)

        self._popup = _MTComboPopup(self)
        self.sync_content_width()

    def sizeHint(self) -> QSize:
        return self._content_size_hint()

    def minimumSizeHint(self) -> QSize:
        return self._content_size_hint()

    def _content_size_hint(self) -> QSize:
        text = self.currentText()
        text_width = self._visual_text_size(text).width() if text else 1
        return QSize(
            max(1, text_width + int(round(self._button_width()))),
            max(1, self._visual_text_size(text).height() if text else self.fontMetrics().height()),
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
        self.sync_content_width()
        self._popup.mark_dirty()
        self.update()

    def addItems(self, texts: list[str]) -> None:
        for text in texts:
            self.addItem(text)

    def clear(self) -> None:
        had_current = self._current_index
        self._items.clear()
        self._current_index = -1
        self.sync_content_width()
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
        self.sync_content_width()
        self._popup.sync_items()
        self.update()

    def itemData(self, index: int, role: int = Qt.ItemDataRole.UserRole) -> object:
        if not 0 <= index < self.count():
            return None
        roles = object_map(self._items[index].get('roles'))
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

    def sync_content_width(self) -> None:
        content_width = 0
        match str(self._content_width_mode).strip().lower():
            case 'none':
                content_width = 0
            case 'current':
                current_text = self.currentText()
                content_width = self._visual_text_size(current_text).width() if current_text else 0
            case _:
                for index in range(self.count()):
                    content_width = max(content_width, self._visual_text_size(self.itemText(index)).width())

        target_width = max(self._content_width_floor, content_width + int(round(self._button_width())))
        self.setMinimumWidth(target_width)

    def set_content_width_mode(self, mode: str) -> None:
        normalized = str(mode or 'longest').strip().lower()
        if normalized not in {'none', 'current', 'longest'}:
            normalized = 'longest'
        if normalized == self._content_width_mode:
            return
        self._content_width_mode = normalized
        if normalized == 'none':
            self.setMinimumWidth(max(self._content_width_floor, int(round(self._button_width()))))
        self.sync_content_width()

    def content_width_mode(self) -> str:
        return self._content_width_mode

    def _popup_object_name(self) -> str:
        base_name = self.objectName().strip() or type(self).__name__
        return f'{base_name}_Popup'

    def _popup_item_object_name(self, index: int) -> str:
        base_name = self.objectName().strip() or type(self).__name__
        return f'{base_name}_Popup_Item_{index}'

    def popup_object_name(self) -> str:
        return self._popup_object_name()

    def popup_item_object_name(self, index: int) -> str:
        return self._popup_item_object_name(index)

    def combo_parts(self) -> dict[str, WidgetThemeMap]:
        return self._parts

    def _build_default_parts(self) -> dict[str, WidgetThemeMap]:
        transparent = QColor(Qt.GlobalColor.transparent)
        return {
            'button': {
                'background_color': QColor(transparent),
                'background_gradient': None,
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
                'background_gradient': None,
                'border_color': QColor(Qt.GlobalColor.transparent),
                'border_width': 0.0,
                'border_style': 'solid',
                'border_radius': None,
                'width': None,
                'height': None,
            },
            'item': {
                'background_color': QColor(Qt.GlobalColor.transparent),
                'background_gradient': None,
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
                        'background_gradient': None,
                        'text_color': QColor(),
                        'border_color': QColor(),
                    },
                    'selected': {
                        'background_color': QColor(),
                        'background_gradient': None,
                        'text_color': QColor(),
                        'border_color': QColor(),
                    },
                },
            },
        }

    def reset_theme(self) -> None:
        self._parts = deepcopy(self._default_parts)
        self._apply_popup_view_theme()
        self.update()

    def _part_data(self, part: str) -> WidgetThemeMap:
        return self._parts.setdefault(part, {})

    def _existing_part_data(self, part: str) -> WidgetThemeMap | None:
        return self._parts.get(part)

    def _item_states(self) -> WidgetThemeMap | None:
        return theme_map(self._part_data('item').get('states'))

    def apply_theme(self, data: WidgetThemeMap) -> None:
        button = theme_map(data.get('button')) or {}
        icon = theme_map(data.get('icon')) or {}
        popup = theme_map(data.get('popup')) or {}
        item = theme_map(data.get('item')) or {}

        if button:
            button_part = self._part_data('button')
            background = theme_map(button.get('background')) or {}
            border = theme_map(button.get('border')) or {}
            if (color := to_qcolor(background.get('color'))) is not None:
                button_part['background_color'] = color
                button_part['background_gradient'] = None
            if isinstance((gradient := normalize_gradient_data(background.get('gradient'))), dict):
                button_part['background_gradient'] = gradient
            if (border_color := to_qcolor(border.get('color'))) is not None:
                button_part['border_color'] = border_color
            if (border_width := coerce_number(border.get('width'))) is not None:
                button_part['border_width'] = max(0.0, border_width)
            if isinstance((border_style := border.get('style')), str) and border_style.strip():
                button_part['border_style'] = border_style.strip().lower()
            if border.get('radius') is not None:
                button_part['border_radius'] = border.get('radius')
            if (width := coerce_number(button.get('width'))) is not None:
                button_part['width'] = max(0.0, width)

        if icon:
            icon_part = self._part_data('icon')
            if (color := to_qcolor(icon.get('color'))) is not None:
                icon_part['color'] = color
            if (size := coerce_number(icon.get('size'))) is not None:
                icon_part['size'] = max(0.0, size)
            if (rotation := coerce_number(icon.get('rotation'))) is not None:
                icon_part['rotation'] = float(rotation)
            source = icon.get('source', icon.get('path', icon.get('file')))
            if isinstance(source, str):
                icon_part['source'] = source.strip()

        self._apply_popup_part_theme('popup', popup)
        self._apply_popup_item_theme('item', item)
        self.sync_content_width()
        self._apply_popup_view_theme()
        self.update()

    def apply_dropdown_theme(self, data: WidgetThemeMap) -> None:
        self._apply_popup_part_theme('popup', data)
        if (text := theme_map(data.get('text'))) is not None:
            self._apply_popup_item_theme('item', {'text': text})
        if (selection := theme_map(data.get('selection'))) is not None:
            self._apply_popup_item_state_theme('selected', selection)
        self._apply_popup_view_theme()
        self.update()

    def apply_items_theme(self, data: WidgetThemeMap) -> None:
        base_theme = {key: value for key, value in data.items() if key not in {'selection', 'qss'}}
        self._apply_popup_item_theme('item', base_theme)
        if (selection := theme_map(data.get('selection'))) is not None:
            self._apply_popup_item_state_theme('selected', selection)
        self._apply_popup_view_theme()
        self.update()

    def _apply_popup_part_theme(self, part: str, data: WidgetThemeMap) -> None:
        part_data = self._part_data(part)
        background = theme_map(data.get('background')) or {}
        border = theme_map(data.get('border')) or {}
        if (color := to_qcolor(background.get('color'))) is not None:
            part_data['background_color'] = color
            part_data['background_gradient'] = None
        if isinstance((gradient := normalize_gradient_data(background.get('gradient'))), dict):
            part_data['background_gradient'] = gradient
        if (border_color := to_qcolor(border.get('color'))) is not None:
            part_data['border_color'] = border_color
        if (border_width := coerce_number(border.get('width'))) is not None:
            part_data['border_width'] = max(0.0, border_width)
        if isinstance((border_style := border.get('style')), str) and border_style.strip():
            part_data['border_style'] = border_style.strip().lower()
        if border.get('radius') is not None:
            part_data['border_radius'] = border.get('radius')
        if part == 'popup':
            if (width := coerce_number(data.get('width'))) is not None:
                part_data['width'] = max(0.0, width)
            if (height := coerce_number(data.get('height'))) is not None:
                part_data['height'] = max(0.0, height)

    def _apply_popup_item_theme(self, part: str, data: WidgetThemeMap) -> None:
        self._apply_popup_part_theme(part, data)
        part_data = self._part_data(part)
        text = theme_map(data.get('text')) or {}
        if (text_color := to_qcolor(text.get('color'))) is not None:
            part_data['text_color'] = text_color
        if (height := coerce_number(data.get('height'))) is not None:
            part_data['height'] = max(1.0, height)
        if (padding := coerce_box_sides(data.get('padding'))) is not None:
            part_data['padding'] = padding

        states = theme_map(data.get('states')) or {}
        for state_name in ('hover', 'selected'):
            self._apply_popup_item_state_theme(state_name, states.get(state_name))

    def _apply_popup_item_state_theme(self, state_name: str, data: object) -> None:
        state_theme = theme_map(data)
        if state_theme is None:
            return

        state = self._item_state_data(state_name)
        if state is None:
            return

        background = theme_map(state_theme.get('background')) or {}
        text = theme_map(state_theme.get('text')) or {}
        border = theme_map(state_theme.get('border')) or {}
        if (color := to_qcolor(background.get('color'))) is not None:
            state['background_color'] = color
            state['background_gradient'] = None
        if isinstance((gradient := normalize_gradient_data(background.get('gradient'))), dict):
            state['background_gradient'] = gradient
        if (text_color := to_qcolor(text.get('color'))) is not None:
            state['text_color'] = text_color
        if (border_color := to_qcolor(border.get('color'))) is not None:
            state['border_color'] = border_color

    def _item_state_data(self, state_name: str) -> WidgetThemeMap | None:
        states = self._item_states()
        if states is None:
            return None
        state = states.get(state_name)
        return theme_map(state)

    def current_part_color(self, part: str, css_name: str = 'background-color') -> QColor:
        if part == 'item' and css_name.startswith('states.'):
            color = self._item_state_color(css_name)
            return QColor(color) if isinstance(color, QColor) and color.isValid() else QColor()

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

    def _item_state_color(self, css_name: str) -> QColor | None:
        path = css_name.split('.')
        if len(path) != 3 or path[0] != 'states':
            return None

        state = self._item_state_data(path[1])
        if state is None:
            return None

        match path[2]:
            case 'background-color':
                key = 'background_color'
            case 'color':
                key = 'text_color'
            case 'border-color':
                key = 'border_color'
            case _:
                return None

        color = state.get(key)
        return color if isinstance(color, QColor) else None

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
                data['background_gradient'] = None
        else:
            data['background_color'] = QColor(color)
            if 'background_gradient' in data:
                data['background_gradient'] = None
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
        if path == ('background', 'gradient'):
            return self.set_part_gradient(part, value)
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
        state = self._item_state_data(state_name)
        if state is None:
            return False

        if path == ('background', 'color'):
            color = to_qcolor(value)
            if color is None:
                return False
            state['background_color'] = QColor(color)
            state['background_gradient'] = None
        elif path == ('background', 'gradient'):
            gradient = normalize_gradient_data(value)
            if not isinstance(gradient, dict):
                return False
            state['background_gradient'] = gradient
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

    def current_part_gradient(self, part: str) -> WidgetThemeMap | None:
        data = self._existing_part_data(part)
        gradient = theme_map(data.get('background_gradient')) if data is not None else None
        return dict(gradient) if gradient is not None else None

    def set_part_gradient(self, part: str, value: object) -> bool:
        data = self._existing_part_data(part)
        gradient = normalize_gradient_data(value)
        if data is None or not isinstance(gradient, dict) or 'background_gradient' not in data:
            return False
        data['background_gradient'] = gradient
        self._refresh_part(part)
        return True

    def current_part_metric(self, part: str, metric_path: tuple[str, ...], fallback: float = 0.0) -> float:
        data = self._existing_part_data(part)
        if data is None:
            return float(fallback)
        if metric_path == ('border', 'width'):
            return float(coerce_number(data.get('border_width')) or fallback)
        if metric_path == ('border', 'radius'):
            radius = data.get('border_radius')
            radius_value = coerce_number(radius)
            return float(radius_value if radius_value is not None else fallback)
        if metric_path == ('width',):
            if part == 'popup':
                return float(self._popup_target_width())
            return float(coerce_number(data.get('width')) or fallback)
        if metric_path == ('size',):
            return float(coerce_number(data.get('size')) or fallback)
        if metric_path == ('rotation',):
            return float(coerce_number(data.get('rotation')) or fallback)
        if metric_path == ('height',):
            if part == 'popup':
                return float(self._popup_target_height())
            return float(coerce_number(data.get('height')) or fallback)
        return float(fallback)

    def set_part_metric(self, part: str, metric_path: tuple[str, ...] | str, value: float) -> bool:
        data = self._existing_part_data(part)
        if data is None:
            return False
        if isinstance(metric_path, str):
            metric_path = (metric_path,)

        if metric_path == ('border', 'width') and 'border_width' in data:
            data['border_width'] = max(0.0, float(value))
        elif metric_path == ('border', 'radius') and 'border_radius' in data:
            data['border_radius'] = max(0.0, float(value))
        elif metric_path == ('width',) and part == 'button':
            data['width'] = max(0.0, float(value))
            self.sync_content_width()
        elif metric_path == ('width',) and part == 'popup':
            data['width'] = max(0.0, float(value))
        elif metric_path == ('size',) and part == 'icon':
            data['size'] = max(0.0, float(value))
        elif metric_path == ('rotation',) and part == 'icon':
            data['rotation'] = float(value)
        elif metric_path == ('height',) and part == 'popup':
            data['height'] = max(0.0, float(value))
        elif metric_path == ('height',) and part == 'item':
            data['height'] = max(1.0, float(value))
        else:
            return False
        self._refresh_part(part)
        return True

    def _refresh_part(self, part: str) -> None:
        if part in {'popup', 'item'}:
            self._apply_popup_view_theme()
            try:
                self._sync_popup_geometry()
                self._popup.update()
                self._popup.sync_items()
            except RuntimeError:
                pass
        self.update()
        self.updateGeometry()

    def _part_background_brush(self, part: str, rect: QRectF):
        data = self._part_data(part)
        brush = build_background_brush(rect, {'gradient': data.get('background_gradient')})
        if brush is not None:
            return brush
        color = data.get('background_color')
        if isinstance(color, QColor) and color.isValid():
            return color
        return Qt.BrushStyle.NoBrush

    def _apply_popup_view_theme(self) -> None:
        try:
            self._popup.apply_shape_mask()
            self._popup.update()
            self._popup.sync_items()
        except RuntimeError:
            return

    def _popup_item_height(self) -> int:
        height = self._part_data('item').get('height')
        if isinstance(height, (int, float)) and float(height) > 0:
            return int(round(float(height)))
        return max(1, self.fontMetrics().height())

    def popup_item_height(self) -> int:
        return self._popup_item_height()

    def _popup_content_height(self) -> int:
        return max(0, self.count() * self._popup_item_height())

    def _popup_target_width(self) -> int:
        requested = coerce_number(self._part_data('popup').get('width'))
        if requested is not None:
            return max(0, int(round(requested)))
        return max(1, self.width())

    def popup_target_width(self) -> int:
        return self._popup_target_width()

    def _popup_target_height(self) -> int:
        requested = coerce_number(self._part_data('popup').get('height'))
        content_height = self._popup_content_height()
        if requested is not None:
            if content_height > 0:
                return max(0, min(int(round(requested)), content_height))
            return max(0, int(round(requested)))
        return max(1, content_height)

    def popup_target_height(self) -> int:
        return self._popup_target_height()

    def _sync_popup_geometry(self) -> None:
        try:
            self._popup.isVisible()
        except RuntimeError:
            return

        width = max(1, self._popup_target_width())
        height = max(1, self._popup_target_height())
        self._popup.setFixedWidth(width)
        self._popup.setFixedHeight(height)
        self._popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self._popup.apply_shape_mask()

    def sync_popup_geometry(self) -> None:
        self._sync_popup_geometry()

    def _popup_item_value(self, state_name: str | None, key: str) -> object:
        value = None
        state = self._item_state_data(state_name) if state_name else None
        if state is not None:
            value = state.get(key)
        if isinstance(value, QColor) and value.isValid():
            return value
        if value is not None and key == 'background_gradient':
            return value
        return self._part_data('item').get(key)

    def _draw_popup_item_background(self, painter: QPainter, rect: QRectF, state_name: str | None) -> None:
        item_part = self._part_data('item')
        color = self._popup_item_value(state_name, 'background_color')
        border_color = self._popup_item_value(state_name, 'border_color')
        border_width = float(coerce_number(item_part.get('border_width')) or 0.0)
        border_style = self._pen_style(item_part.get('border_style', 'solid'))
        radius = self._resolve_radius(item_part.get('border_radius'), rect)

        painter.save()
        brush = build_background_brush(rect, {'gradient': self._popup_item_value(state_name, 'background_gradient')})
        if brush is not None:
            painter.setBrush(brush)
        elif isinstance(color, QColor) and color.isValid():
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        painter.drawPath(self._rounded_path(draw_rect, radius))
        painter.restore()

    def draw_popup_item_background(self, painter: QPainter, rect: QRectF, state_name: str | None) -> None:
        self._draw_popup_item_background(painter, rect, state_name)

    def _draw_popup_background(self, painter: QPainter, rect: QRectF) -> None:
        popup = self._part_data('popup')
        border_width = float(coerce_number(popup.get('border_width')) or 0.0)
        border_color = popup.get('border_color')
        border_style = self._pen_style(popup.get('border_style', 'solid'))

        painter.save()
        brush = build_background_brush(rect, {'gradient': popup.get('background_gradient')})
        if brush is not None:
            painter.setBrush(brush)
        elif isinstance((background := popup.get('background_color')), QColor) and background.isValid():
            painter.setBrush(background)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        radius = self._resolve_radius(popup.get('border_radius'), draw_rect)
        painter.drawPath(self._rounded_path(draw_rect, radius))
        painter.restore()

    def draw_popup_background(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_popup_background(painter, rect)

    def _draw_popup_item_text(self, painter: QPainter, rect: QRectF, state_name: str | None, text: str) -> None:
        color = self._popup_item_value(state_name, 'text_color')
        if not isinstance(color, QColor) or not color.isValid():
            color = self.palette().color(self.foregroundRole())

        painter.save()
        painter.setFont(self.font())
        padding = cast(tuple[object, object, object, object], self._part_data('item').get('padding', (0.0, 0.0, 0.0, 0.0)))
        top, right, bottom, left = padding
        text_rect = rect.adjusted(
            float(coerce_number(left) or 0.0),
            float(coerce_number(top) or 0.0),
            -float(coerce_number(right) or 0.0),
            -float(coerce_number(bottom) or 0.0),
        )
        self._draw_themed_text(
            painter,
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
            color,
        )
        painter.restore()

    def draw_popup_item_text(self, painter: QPainter, rect: QRectF, state_name: str | None, text: str) -> None:
        self._draw_popup_item_text(painter, rect, state_name, text)

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
            self._sync_popup_geometry()
            self._popup.raise_()

    def _activate_popup_item(self, index: int) -> None:
        self.setCurrentIndex(index)
        self.activated.emit(index)
        self.hidePopup()

    def activate_popup_item(self, index: int) -> None:
        self._activate_popup_item(index)

    def _on_popup_hidden(self) -> None:
        close_notified = self._popup_close_notified
        self._popup_close_notified = False
        if self._popup_hide_expected:
            self._popup_hide_expected = False
        else:
            self._suppress_next_mouse_press = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if not close_notified:
            self.popupClosed.emit()

    def on_popup_hidden(self) -> None:
        self._on_popup_hidden()

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
        self._draw_themed_text(
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
        painter.setBrush(self._part_background_brush('button', rect))

        button_part = self._part_data('button')
        border_width = float(coerce_number(button_part.get('border_width')) or 0.0)
        border_color = button_part.get('border_color')
        border_style = self._pen_style(button_part.get('border_style', 'solid'))
        if border_width > 0 and isinstance(border_color, QColor) and border_color.isValid() and border_style != Qt.PenStyle.NoPen:
            pen = QPen(border_color, border_width)
            pen.setStyle(border_style)
            painter.setPen(pen)
            inset = border_width / 2.0
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            inset = 0.0

        draw_rect = rect.adjusted(inset, inset, -inset, -inset)
        radius = self._resolve_radius(button_part.get('border_radius'), draw_rect)
        painter.drawPath(self._rounded_path(draw_rect, radius))
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

    def _resolve_radius(self, value: object, rect: QRectF) -> float:
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

    def resolve_radius(self, value: object, rect: QRectF) -> float:
        return self._resolve_radius(value, rect)

    def _rounded_path(self, rect: QRectF, radius: float) -> QPainterPath:
        path = QPainterPath()
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
            return path
        path.addRoundedRect(rect, radius, radius)
        return path

    def rounded_path(self, rect: QRectF, radius: float) -> QPainterPath:
        return self._rounded_path(rect, radius)

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


class MTScrollArea(BoxThemeMixin, QScrollArea):
    PAINTED_BOX_THEME = False

    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.init_box_theme()
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

    def apply_box_theme(self, theme: dict[str, Any]) -> None:
        content = self.widget()
        apply_box_theme = getattr(content, 'apply_box_theme', None)
        if callable(apply_box_theme):
            self._box_theme = None
            apply_box_theme(theme)
            self.viewport().update()
            return
        super().apply_box_theme(theme)

    def clear_box_theme(self) -> None:
        content = self.widget()
        clear_box_theme = getattr(content, 'clear_box_theme', None)
        if callable(clear_box_theme):
            clear_box_theme()
        super().clear_box_theme()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)


class MTWidget(BoxThemeMixin, QWidget):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.init_box_theme()

        if obj_name:
            self.setObjectName(obj_name)

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.has_box_theme():
            painter = new_widget_painter(self, antialias=False)
            draw_widget_background(self, painter)
            painter.end()
            super().paintEvent(event)
            return

        painter = new_widget_painter(self)
        self.draw_box_theme(painter)
        painter.end()


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
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
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

    def set_items(self, items: Sequence[str], *, preferred: str | None = None) -> bool:
        target = preferred if preferred in items else items[0] if items else None
        if self._plain_values() == [str(item) for item in items]:
            self.list_widget.setCurrentValue(target)
            return False

        self.list_widget.clear()
        for name in items:
            self.list_widget.add_item(name, name)
        self.list_widget.setCurrentValue(target)
        return True

    def set_grouped_items(
        self,
        groups: Sequence[tuple[str, Sequence[tuple[str, str]]]],
        *,
        preferred: str | None = None,
    ) -> None:
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
        tr_key: str = 'Upload or Drag & Drop text/files here',
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
