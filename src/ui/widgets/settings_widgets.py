import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QObject, QSignalBlocker, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QFileDialog, QSizePolicy, QVBoxLayout, QWidget

from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.theme.colors import to_qcolor
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTButton,
    MTDoubleSpinBox,
    MTLabel,
    MTLineEdit,
    MTScrollArea,
    MTSlider,
    MTSpinBox,
    MTWidget,
)
from src.ui.widgets.custom import MTComboBox, MTSwitch
from src.utils.constants import PATH_CONTAINER_ARROW_ICON, ROOT
from src.utils.regexes import NORMALIZE_QT_KEY_PATTERN

SETTING_ROW_HEIGHT = 0
SETTING_ROW_GAP = 0
SLIDER_COMPACT_PART_HEIGHT = 0
COLLAPSIBLE_TOGGLE_BUTTON_SIZE = 20
COLLAPSIBLE_TOGGLE_ICON_SIZE = 18
_COLUMN_REBALANCE_EVENT_TYPES = {
    QEvent.Type.Show,
    QEvent.Type.Hide,
}


@lru_cache(maxsize=64)
def _icon(source: str, color_name: str, rotation: float, size: int) -> QIcon:
    base_pixmap = QIcon(source).pixmap(QSize(size, size))
    if base_pixmap.isNull():
        return QIcon()

    tinted_pixmap = QPixmap(base_pixmap.size())
    tinted_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted_pixmap)
    painter.drawPixmap(0, 0, base_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted_pixmap.rect(), QColor(color_name))
    painter.end()

    rotated_pixmap = tinted_pixmap.transformed(
        QTransform().rotate(rotation), Qt.TransformationMode.SmoothTransformation
    )
    return QIcon(rotated_pixmap)


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        widget.update()
        return

    if not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
        widget.update()
        return

    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _measure(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    text = value.strip().lower()
    if not text or text.endswith("%"):
        return None
    if text.endswith("px"):
        text = text[:-2].strip()
    try:
        return float(text)
    except ValueError:
        return None


def _positive_int(value: Any) -> int | None:
    number = _measure(value)
    if number is None:
        return None
    return max(1, int(round(number)))


def _theme_icon_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    path = Path(value.strip()).expanduser()
    if path.is_absolute():
        return str(path)

    root_path = ROOT / path
    if root_path.exists():
        return str(root_path)

    return str(path)


class MTColumnsSetting(MTScrollArea):
    def __init__(
        self,
        tabs: list[QWidget] | None = None,
        columns: int = 2,
        obj_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        self._tabs: list[QWidget] = []
        self._rebalancing = False
        super().__init__(parent)

        self._columns = max(1, int(columns))
        self._layouts: list[QVBoxLayout] = []
        self._column_heights: list[int] = [0 for _ in range(self._columns)]
        self._column_assignments: tuple[tuple[int, ...], ...] = tuple(
            tuple() for _ in range(self._columns)
        )
        self._rebalance_timer = QTimer(self)
        self._rebalance_timer.setSingleShot(True)
        self._rebalance_timer.setInterval(0)
        self._rebalance_timer.timeout.connect(self._rebalance_columns)
        if obj_name:
            self.setObjectName(f"{obj_name}_Columns_Widget")
        content_obj_name = f"{obj_name}_Columns_Content_Widget" if obj_name else ""
        self._scroll_area_content = MTWidget(obj_name=content_obj_name)
        self.setWidget(self._scroll_area_content)

        self._main_layout = create_layout(
            LayoutType.HBOX, parent=self._scroll_area_content
        )

        for index in range(self._columns):
            column_widget = MTWidget(
                obj_name=f"{obj_name}_Columns_{index}_Column_Widget" if obj_name else ""
            )
            column_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            column_widget.setMinimumWidth(0)
            column_layout = create_layout(LayoutType.VBOX, parent=column_widget)
            self._main_layout.addWidget(column_widget, stretch=1)
            self._layouts.append(column_layout)

        for layout in self._layouts:
            layout.addStretch()

        if tabs is not None:
            for tab in tabs:
                self.add_tab(tab)

        self._rebalance_columns()

    def add_tab(self, tab: QWidget) -> None:
        if not isinstance(tab, QWidget):
            return

        self._tabs.append(tab)
        self._attach_tab_observers(tab)
        self.request_rebalance()

    def request_rebalance(self) -> None:
        if self._rebalancing:
            return
        self._rebalance_timer.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._tabs and event.type() in _COLUMN_REBALANCE_EVENT_TYPES:
            self.request_rebalance()
        return super().eventFilter(watched, event)

    def _rebalance_columns(self) -> None:
        if self._rebalancing:
            return

        self._rebalance_timer.stop()
        self._rebalancing = True
        try:
            self._prepare_tabs_for_measurement()
            assignments, heights = self._build_column_plan()
            if assignments != self._column_assignments:
                self._apply_column_plan(assignments)
            self._column_heights = heights

            self._scroll_area_content.updateGeometry()
            self.widget().updateGeometry()
            self.updateGeometry()
        finally:
            self._rebalancing = False

    def _attach_tab_observers(self, tab: QWidget) -> None:
        tab.installEventFilter(self)
        toggled = getattr(tab, "toggled", None)
        if toggled is None:
            return

        try:
            toggled.connect(lambda *_args: self.request_rebalance())
        except Exception:
            return

    def _target_column_index(self) -> int:
        return min(
            range(len(self._column_heights)),
            key=lambda index: self._column_heights[index],
        )

    def _build_column_plan(self) -> tuple[tuple[tuple[int, ...], ...], list[int]]:
        self._column_heights = [0 for _ in range(self._columns)]
        columns: list[list[int]] = [[] for _ in range(self._columns)]

        for tab_index, tab in enumerate(self._tabs):
            column_index = self._target_column_index()
            columns[column_index].append(tab_index)
            self._column_heights[column_index] += (
                self._estimated_tab_height(tab) + SETTING_ROW_GAP
            )

        assignments = tuple(tuple(column) for column in columns)
        heights = list(self._column_heights)
        return assignments, heights

    def _apply_column_plan(self, assignments: tuple[tuple[int, ...], ...]) -> None:
        self._clear_columns()

        for column_index, tab_indexes in enumerate(assignments):
            layout = self._layouts[column_index]
            for tab_index in tab_indexes:
                layout.addWidget(self._tabs[tab_index])
            layout.addStretch()

        self._column_assignments = assignments

    def _prepare_tabs_for_measurement(self) -> None:
        self.ensurePolished()
        self._scroll_area_content.ensurePolished()
        self._main_layout.activate()
        for tab in self._tabs:
            tab.ensurePolished()
            if (layout := tab.layout()) is not None:
                layout.activate()

    def _estimated_tab_height(self, tab: QWidget) -> int:
        height_hint = getattr(tab, "effective_height_hint", None)
        if callable(height_hint):
            try:
                return max(1, int(height_hint()))
            except Exception:
                pass

        fixed_height = tab.minimumHeight()
        if fixed_height > 0 and tab.maximumHeight() == fixed_height:
            return int(fixed_height)
        if tab.height() > 0:
            return int(tab.height())
        minimum_hint = (
            tab.minimumSizeHint().height() if tab.minimumSizeHint().isValid() else 0
        )
        layout_hint = (
            tab.layout().sizeHint().height() if tab.layout() is not None else 0
        )
        return max(1, int(max(tab.sizeHint().height(), minimum_hint, layout_hint)))

    def _clear_columns(self) -> None:
        for layout in self._layouts:
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item is None:
                    continue

                if (widget := item.widget()) is not None:
                    widget.setParent(self._scroll_area_content)


class MTCollapsibleContainer(MTWidget):
    toggled = Signal(bool)

    def __init__(
        self,
        tr_key: str,
        obj_name: str,
        widgets: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"{obj_name}_Container_Widget")

        self._default_toggle_arrow_source = str(PATH_CONTAINER_ARROW_ICON)
        self._default_toggle_arrow_size = COLLAPSIBLE_TOGGLE_ICON_SIZE
        self._default_toggle_button_size = COLLAPSIBLE_TOGGLE_BUTTON_SIZE
        self._default_toggle_arrow_color: str | None = None
        self._default_toggle_arrow_collapsed_rotation = 0.0
        self._default_toggle_arrow_expanded_rotation = 90.0
        self._reset_toggle_arrow_theme_values()
        self._toggle_arrow_rotation = self._default_toggle_arrow_expanded_rotation
        self._content_height_animation_active = False

        self._main_layout = create_layout(LayoutType.VBOX, parent=self)

        self._header_widget = MTWidget(obj_name=f"{obj_name}_Container_Header_Widget")
        self._header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_layout = create_layout(LayoutType.HBOX, parent=self._header_widget)
        self._header_separator = MTWidget(
            obj_name=f"{obj_name}_Container_Header_Separator"
        )
        self._header_separator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._header_separator.setFixedHeight(1)
        self._header_separator.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._label = MTLabel(
            tr_key=tr_key, obj_name=f"{obj_name}_Container_Header_Title"
        )
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._label.setCursor(Qt.CursorShape.PointingHandCursor)

        self._toggle_button = MTButton(
            tr_key="",
            checkable=True,
            checked=True,
            obj_name=f"{obj_name}_Container_Header_Button",
        )
        self._toggle_button.setProperty("rainbowBorderTarget", False)
        self._toggle_button.setProperty("rainbowBorderExcluded", True)
        self._toggle_button.setText("")
        self._apply_toggle_button_metrics()
        self._content_widget = MTWidget(obj_name=f"{obj_name}_Container_Content_Widget")
        self._content_layout = create_layout(
            LayoutType.VBOX, parent=self._content_widget
        )

        self._header_layout.addWidget(self._label)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._toggle_button)
        self._main_layout.addWidget(self._header_widget)
        self._main_layout.addWidget(self._header_separator)
        self._main_layout.addWidget(self._content_widget)

        for widget in widgets or []:
            self._content_layout.addWidget(widget)

        self._header_widget.installEventFilter(self)
        self._label.installEventFilter(self)
        self._content_widget.installEventFilter(self)

        initial_checked = self._toggle_button.isChecked()
        self.setProperty("expanded", initial_checked)
        self._header_widget.setProperty("expanded", initial_checked)
        self._toggle_button.setProperty("expanded", initial_checked)
        self._content_widget.setMaximumHeight(self._content_target_height())
        self._toggle_arrow_rotation = (
            self._toggle_arrow_expanded_rotation
            if initial_checked
            else self._toggle_arrow_collapsed_rotation
        )
        self._refresh_toggle_icon()

        self._toggle_button.toggled.connect(self._toggle_collapsed)
        self._toggle_button.toggled.connect(self.toggled.emit)

    def reset_theme(self) -> None:
        self._reset_toggle_arrow_theme_values()
        if not self._uses_theme_icon_rotation_animation():
            self._toggle_arrow_rotation = (
                self._toggle_arrow_expanded_rotation
                if self._toggle_button.isChecked()
                else self._toggle_arrow_collapsed_rotation
            )
        self._apply_toggle_button_metrics()
        self._refresh_toggle_icon()

    def apply_theme(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        icon = data.get("icon") if isinstance(data.get("icon"), dict) else {}

        if isinstance(icon, dict):
            source = icon.get("source", icon.get("path", icon.get("file")))
            if (icon_path := _theme_icon_path(source)) is not None:
                self._toggle_arrow_source = icon_path

            if "color" in icon:
                color = to_qcolor(icon.get("color"))
                self._toggle_arrow_color = (
                    color.name(QColor.NameFormat.HexArgb) if color is not None else None
                )

            if (size := _positive_int(icon.get("size"))) is not None:
                self._toggle_arrow_size = size

            button_size = icon.get(
                "button_size", icon.get("button-size", icon.get("buttonSize"))
            )
            if button_size is None and isinstance(icon.get("button"), dict):
                button_size = icon["button"].get("size")
            if (parsed_button_size := _positive_int(button_size)) is not None:
                self._toggle_button_size = parsed_button_size

            collapsed_rotation = icon.get(
                "collapsed_rotation",
                icon.get("collapsed-rotation", icon.get("collapsed")),
            )
            expanded_rotation = icon.get(
                "expanded_rotation", icon.get("expanded-rotation", icon.get("expanded"))
            )
            if isinstance(icon.get("rotation"), dict):
                rotation = icon["rotation"]
                collapsed_rotation = rotation.get("collapsed", collapsed_rotation)
                expanded_rotation = rotation.get("expanded", expanded_rotation)
            if (parsed_collapsed := _measure(collapsed_rotation)) is not None:
                self._toggle_arrow_collapsed_rotation = parsed_collapsed
            if (parsed_expanded := _measure(expanded_rotation)) is not None:
                self._toggle_arrow_expanded_rotation = parsed_expanded

        if not self._uses_theme_icon_rotation_animation():
            self._toggle_arrow_rotation = (
                self._toggle_arrow_expanded_rotation
                if self._toggle_button.isChecked()
                else self._toggle_arrow_collapsed_rotation
            )
        self._apply_toggle_button_metrics()
        self._refresh_toggle_icon()
        if self._toggle_button.isChecked():
            self._sync_content_height_to_layout()

    def _toggle_collapsed(self, checked: bool) -> None:
        self.setProperty("expanded", checked)
        self._header_widget.setProperty("expanded", checked)
        self._toggle_button.setProperty("expanded", checked)

        if self._uses_theme_content_height_animation():
            if checked:
                self._content_widget.setMaximumHeight(0)
                self._content_widget.setVisible(True)
                self._header_separator.setVisible(True)
        else:
            target_height = self._content_target_height() if checked else 0
            self.set_part_metric("content", ("height",), float(target_height))
        if self._uses_theme_icon_rotation_animation():
            self._refresh_toggle_icon()
        else:
            target_rotation = (
                self._toggle_arrow_expanded_rotation
                if checked
                else self._toggle_arrow_collapsed_rotation
            )
            self.set_part_metric("icon", ("rotation",), target_rotation)
        _repolish(self)
        _repolish(self._header_widget)
        _repolish(self._header_separator)
        _repolish(self._toggle_button)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            watched in {self._header_widget, self._label}
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            if (
                isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
            ):
                header_pos = event.position().toPoint()
                if watched is not self._header_widget and isinstance(watched, QWidget):
                    header_pos = watched.mapTo(self._header_widget, header_pos)
                if not self._toggle_button.geometry().contains(header_pos):
                    self._toggle_button.setChecked(not self._toggle_button.isChecked())
                    return True
        if (
            watched is self._content_widget
            and event.type() == QEvent.Type.LayoutRequest
        ):
            self._sync_content_height_to_layout()
        return super().eventFilter(watched, event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.EnabledChange,
        }:
            self._refresh_toggle_icon()

    def _reset_toggle_arrow_theme_values(self) -> None:
        self._toggle_arrow_source = self._default_toggle_arrow_source
        self._toggle_arrow_size = self._default_toggle_arrow_size
        self._toggle_button_size = self._default_toggle_button_size
        self._toggle_arrow_color = self._default_toggle_arrow_color
        self._toggle_arrow_collapsed_rotation = (
            self._default_toggle_arrow_collapsed_rotation
        )
        self._toggle_arrow_expanded_rotation = (
            self._default_toggle_arrow_expanded_rotation
        )

    def _apply_toggle_button_metrics(self) -> None:
        button_size = max(self._toggle_arrow_size, self._toggle_button_size)
        self._toggle_button.setMinimumSize(button_size, button_size)
        self._toggle_button.setIconSize(
            QSize(self._toggle_arrow_size, self._toggle_arrow_size)
        )

    def _refresh_toggle_icon(self) -> None:
        self._toggle_button.setIcon(
            self._current_toggle_icon(self._toggle_arrow_rotation)
        )

    def _current_toggle_icon(self, rotation: float) -> QIcon:
        color = (
            self._toggle_arrow_color
            or self._toggle_button.palette()
            .buttonText()
            .color()
            .name(QColor.NameFormat.HexArgb)
        )
        return _icon(
            self._toggle_arrow_source, color, rotation, self._toggle_arrow_size
        )

    def _content_target_height(self) -> int:
        return max(0, self._content_layout.sizeHint().height())

    def effective_height_hint(self) -> int:
        self.ensurePolished()
        self._content_layout.activate()
        self._main_layout.activate()

        margins = self._main_layout.contentsMargins()
        spacing = max(0, self._main_layout.spacing())
        header_height = max(
            1,
            int(
                max(
                    self._header_widget.sizeHint().height(),
                    self._label.sizeHint().height(),
                    self._toggle_button.sizeHint().height(),
                )
            ),
        )
        separator_height = int(
            self._header_separator.height()
            or self._header_separator.sizeHint().height()
            or 0
        )
        content_height = (
            self._content_target_height() if self._toggle_button.isChecked() else 0
        )

        total = margins.top() + margins.bottom() + header_height
        if separator_height > 0:
            total += spacing + separator_height
        if content_height > 0:
            total += spacing + content_height
        return max(1, total)

    def _sync_content_height_to_layout(self) -> None:
        if not self._toggle_button.isChecked():
            return
        if self._content_height_animation_active:
            return

        target_height = self._content_target_height()
        if target_height <= 0:
            return

        if self._content_widget.maximumHeight() != target_height:
            self._content_widget.setMaximumHeight(target_height)
        self._content_widget.setVisible(True)
        self._header_separator.setVisible(True)
        self._content_layout.invalidate()
        self._main_layout.invalidate()
        self._content_widget.updateGeometry()
        self.updateGeometry()

    def isCheckable(self) -> bool:
        return True

    def isChecked(self) -> bool:
        return self._toggle_button.isChecked()

    def current_part_metric(
        self, part: str, path: tuple[str, ...], fallback: float
    ) -> float:
        if part == "icon" and path and path[0] == "rotation":
            return float(self._toggle_arrow_rotation)

        if part != "content" or not path or path[0] not in {"height", "size"}:
            return float(fallback)

        maximum_height = self._content_widget.maximumHeight()
        if maximum_height >= 16777215:
            return float(
                max(self._content_widget.height(), self._content_target_height())
            )
        return float(maximum_height)

    def set_part_metric(
        self, part: str, path: tuple[str, ...] | str, value: float
    ) -> bool:
        tokens = (path,) if isinstance(path, str) else tuple(path)
        if part == "icon" and tokens and tokens[0] == "rotation":
            self._toggle_arrow_rotation = float(value)
            self._refresh_toggle_icon()
            return True

        if part != "content":
            return False

        if not tokens or tokens[0] not in {"height", "size"}:
            return False

        target_height = self._content_target_height()
        resolved_value = max(0.0, float(value))
        if target_height > 0:
            resolved_value = min(resolved_value, float(target_height))

        height = max(0, int(round(resolved_value)))
        if height > 0:
            self._content_widget.setVisible(True)
            self._header_separator.setVisible(True)
        self._content_widget.setMaximumHeight(height)
        self._content_layout.invalidate()
        self._main_layout.invalidate()
        self._content_widget.updateGeometry()
        self.updateGeometry()
        if height <= 0:
            self._content_widget.setVisible(False)
            self._header_separator.setVisible(False)
        return True

    def normalize_part_metric(
        self, part: str, path: tuple[str, ...], value: float
    ) -> float:
        if part == "icon" and path and path[0] == "rotation":
            return float(value)
        if part == "content" and path and path[0] in {"height", "size"}:
            target_height = self._content_target_height()
            resolved_value = max(0.0, float(value))
            if target_height > 0:
                resolved_value = min(resolved_value, float(target_height))
            return resolved_value
        return float(value)

    def _uses_theme_content_height_animation(self) -> bool:
        return bool(self.property("_themeAnimatedContentHeight"))

    def _uses_theme_icon_rotation_animation(self) -> bool:
        return bool(self.property("_themeAnimatedArrowRotation"))

    def handle_part_animation_state(
        self, part: str, path: tuple[str, ...], active: bool
    ) -> None:
        if part == "content" and path and path[0] in {"height", "size"}:
            self._content_height_animation_active = bool(active)
            if not active and self._toggle_button.isChecked():
                self._sync_content_height_to_layout()


class MTButtonSetting(MTButton):
    def __init__(
        self,
        tr_key: str,
        action: Callable[[], None],
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr_key=tr_key, obj_name=f"{obj_name}_Setting", parent=parent)
        self.setProperty("rainbowBorderTarget", True)
        self.clicked.connect(action)


class MTCheckBoxSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_CheckBox_Setting")
        self.setProperty("rainbowBorderTarget", False)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._check_box = MTSwitch(obj_name=f"{obj_name}_CheckBox")
        self._check_box.setChecked(
            bool(self._config.get(self._cfg_key, default=default))
        )

        self._check_box.toggled.connect(lambda v: self._config.set(self._cfg_key, v))
        self._config.config_loaded.connect(
            lambda d=default: self._check_box.setChecked(
                bool(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._check_box)

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._check_box.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )


class MTSwitchSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: bool,
        obj_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        obj_name = obj_name or re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Switch_Setting")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._switch = MTSwitch(obj_name=f"{obj_name}_Switch")
        self._switch.setChecked(bool(self._config.get(self._cfg_key, default=default)))
        self._suspend_config_write = False

        self._switch.toggled.connect(self._on_switch_toggled)
        self._config.config_loaded.connect(
            lambda d=default: self._switch.setChecked(
                bool(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._switch)

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )

    def _on_switch_toggled(self, value: bool) -> None:
        if self._suspend_config_write:
            return
        self._config.set(self._cfg_key, value)

    def set_checked(self, checked: bool, *, emit_signal: bool = True) -> None:
        target = bool(checked)
        if self._switch.isChecked() == target:
            return
        if emit_signal:
            self._switch.setChecked(target)
            return

        self._suspend_config_write = True
        try:
            self._switch.setChecked(target)
        finally:
            self._suspend_config_write = False

    def is_checked(self) -> bool:
        return self._switch.isChecked()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (
                    child is self._switch or self._switch.isAncestorOf(child)
                ):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self.set_checked(not self.is_checked(), emit_signal=True)
                    event.accept()
                    return

        super().mouseReleaseEvent(event)


class MTSwitchRowSetting(MTWidget):
    def __init__(
        self,
        tr_key: str,
        switch: MTSwitch,
        *,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._switch = switch
        self.setObjectName(f"{obj_name}_Switch_Row_Setting")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(
            tr_key=tr_key,
            obj_name=f"{obj_name}_Label",
        )
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._switch)

    @property
    def label(self) -> MTLabel:
        return self._label

    @property
    def switch(self) -> MTSwitch:
        return self._switch

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(
            bounds_height=available_height - 2, bounds_width=max(1, self.width() // 3)
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if child is not None and (
                    child is self._switch or self._switch.isAncestorOf(child)
                ):
                    super().mouseReleaseEvent(event)
                    return

                if self._switch.isEnabled():
                    self._switch.setChecked(not self._switch.isChecked())
                    event.accept()
                    return

        super().mouseReleaseEvent(event)


class MTComboBoxSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        items: list[str | tuple[str, str]],
        default: str,
        on_changed: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        self._on_changed = on_changed
        self._default = default
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_ComboBox_Setting")
        self.setProperty("rainbowBorderTarget", False)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        self._combo_box = MTComboBox(obj_name=f"{obj_name}_ComboBox")
        self._combo_box.setProperty("rainbowBorderTarget", True)
        self._combo_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._combo_box.set_content_width_mode("current")
        self.set_items(items, keep_current=False)

        self._set_current_value(
            self._config.get(self._cfg_key, default=default), fallback=default
        )
        self._combo_box.currentIndexChanged.connect(self._on_index_changed)
        self._config.config_loaded.connect(
            lambda d=default: self._set_current_value(
                self._config.get(self._cfg_key, default=d), fallback=d
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._combo_box, 1)

    def set_items(
        self, items: list[str | tuple[str, str]], *, keep_current: bool = True
    ) -> None:
        current_value: str | None = None
        if keep_current:
            current_index = self._combo_box.currentIndex()
            current_data = self._combo_box.itemData(current_index)
            current_value = (
                str(current_data)
                if current_data is not None
                else self._combo_box.currentText()
            )

        seen: set[str] = set()
        normalized_items: list[tuple[str, str, bool]] = []
        for item in items:
            if isinstance(item, tuple):
                display_text, value = item
                display_value = str(display_text).strip()
                raw_value = str(value).strip()
                translatable = False
            else:
                raw_value = str(item).strip()
                display_value = raw_value
                translatable = True

            value = raw_value
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_items.append((display_value, value, translatable))

        target_value = (
            current_value
            if keep_current
            else str(self._config.get(self._cfg_key, default=self._default))
        )

        with QSignalBlocker(self._combo_box):
            self._combo_box.clear()
            for display_text, value, translatable in normalized_items:
                if translatable:
                    self._combo_box.add_item(value)
                    continue
                self._combo_box.addItem(display_text, value)
            self._set_current_value(target_value, fallback=self._default)
            self._combo_box.sync_content_width()

    def _set_current_value(self, value: str, *, fallback: str | None = None) -> None:
        index = self._find_index(value)
        if index < 0 and fallback is not None:
            index = self._find_index(fallback)
        if index < 0 and self._combo_box.count() > 0:
            index = 0
        if index >= 0:
            self._combo_box.setCurrentIndex(index)

    def _find_index(self, value: str | None) -> int:
        if value is None:
            return -1

        needle = str(value).strip()
        if not needle:
            return -1

        index = self._combo_box.findData(needle)
        if index >= 0:
            return index
        index = self._combo_box.findText(needle)
        if index >= 0:
            return index

        needle_cf = needle.casefold()
        for idx in range(self._combo_box.count()):
            data = self._combo_box.itemData(idx)
            if isinstance(data, str) and data.casefold() == needle_cf:
                return idx
            text = self._combo_box.itemText(idx)
            if isinstance(text, str) and text.casefold() == needle_cf:
                return idx

        return -1

    def _on_index_changed(self, index: int) -> None:
        value = self._combo_box.itemData(index)
        if value is None:
            value = self._combo_box.currentText()
        self._config.set(self._cfg_key, value)
        if callable(self._on_changed):
            self._on_changed(str(value))


class MTTextSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Text_Setting")
        self.setProperty("rainbowBorderTarget", False)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        self._line_edit = MTLineEdit(obj_name=f"{obj_name}_LineEdit")
        self._line_edit.setProperty("rainbowBorderTarget", True)
        self._line_edit.setText(str(self._config.get(self._cfg_key, default=default)))
        self._line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._line_edit.editingFinished.connect(self._on_changed)
        self._config.config_loaded.connect(
            lambda d=default: self._line_edit.setText(
                str(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._line_edit, 1)

    def _on_changed(self) -> None:
        self._config.set(self._cfg_key, self._line_edit.text())


class MTPathSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        default: str,
        *,
        mode: str = "directory",
        file_filter: str = "",
        caption: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        self._mode = str(mode).strip().lower() or "directory"
        self._file_filter = str(file_filter or "")
        self._caption = (
            caption.strip() if isinstance(caption, str) and caption.strip() else None
        )
        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Path_Setting")
        self.setProperty("rainbowBorderTarget", False)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        self._line_edit = MTLineEdit(obj_name=f"{obj_name}_LineEdit")
        self._line_edit.setProperty("rainbowBorderTarget", True)
        self._line_edit.setText(str(self._config.get(self._cfg_key, default=default)))
        self._line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._browse_button = MTButton(tr_key="", obj_name=f"{obj_name}_Browse_Button")
        self._browse_button.setProperty("rainbowBorderTarget", True)
        self._browse_button.setText("")
        self._browse_button.set_text_icon(
            source=str(ROOT / "src/assets/icons/folder.svg"),
            align="center",
            size=QSize(18, 18),
            spacing=0.0,
        )
        self._browse_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        self._line_edit.editingFinished.connect(self._on_changed)
        self._browse_button.clicked.connect(self._browse_path)
        self._config.config_loaded.connect(
            lambda d=default: self._line_edit.setText(
                str(self._config.get(self._cfg_key, default=d))
            )
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._line_edit, 1)
        self._main_layout.addWidget(self._browse_button)

    def _on_changed(self) -> None:
        self._config.set(self._cfg_key, self._line_edit.text())

    def _browse_path(self) -> None:
        caption = self._caption or self._label.text().strip() or "Select path"
        start_path = self._dialog_start_path()

        selected_path = ""
        if self._mode == "open-file":
            selected_path, _ = QFileDialog.getOpenFileName(
                self,
                caption,
                start_path,
                self._file_filter,
            )
        elif self._mode == "save-file":
            selected_path, _ = QFileDialog.getSaveFileName(
                self,
                caption,
                start_path,
                self._file_filter,
            )
        else:
            selected_path = QFileDialog.getExistingDirectory(
                self,
                caption,
                start_path,
            )

        if not selected_path:
            return

        self._line_edit.setText(selected_path)
        self._on_changed()

    def _dialog_start_path(self) -> str:
        text = self._line_edit.text().strip()
        if not text:
            return str(ROOT)

        path = Path(text).expanduser()
        if path.exists():
            if path.is_dir():
                return str(path)
            return str(path.parent)

        parent = path.parent
        if parent.exists():
            return str(parent)
        return str(ROOT)


class MTSliderSetting(MTWidget):
    def __init__(
        self,
        config: Config | ConfigLoader,
        tr_key: str,
        cfg_key: str,
        min_value: int | float,
        max_value: int | float,
        default: int | float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = config
        self._cfg_key = cfg_key
        value = self._config.get(self._cfg_key, default=default)
        self._prev_value = value if min_value <= value <= max_value else default

        obj_name = re.sub(NORMALIZE_QT_KEY_PATTERN, "_", self._cfg_key)
        self.setObjectName(f"{obj_name}_Slider_Setting")

        self._main_layout = create_layout(LayoutType.VBOX, parent=self)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._info_layout = create_layout(LayoutType.HBOX)

        self._label = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Label")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        if isinstance(default, int):
            self._spin_box = MTSpinBox(obj_name=f"{obj_name}_SpinBox")
        else:
            self._spin_box = MTDoubleSpinBox(obj_name=f"{obj_name}_DoubleSpinBox")

        self._spin_box.setRange(min_value, max_value)
        self._spin_box.setValue(self._prev_value)
        self._spin_box.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._spin_box.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )

        self._slider = MTSlider(obj_name=f"{obj_name}_Slider")
        self._slider.setRange(min_value, max_value)
        self._slider.setValue(self._prev_value)

        self._slider.valueChanged.connect(self._spin_box.setValue)
        self._spin_box.valueChanged.connect(self._slider.setValue)
        self._spin_box.editingFinished.connect(
            lambda: self._on_changed(self._spin_box.value())
        )
        self._spin_box.editingFinished.connect(self._spin_box.clearFocus)
        self._slider.sliderReleased.connect(
            lambda: self._on_changed(self._slider.value())
        )
        self._config.config_loaded.connect(
            lambda d=default: self._slider.setValue(
                self._config.get(self._cfg_key, default=d)
            )
        )

        self._info_layout.addWidget(self._label)
        self._info_layout.addStretch()
        self._info_layout.addWidget(self._spin_box)
        self._main_layout.addLayout(self._info_layout)
        self._main_layout.addWidget(self._slider)

    def _on_changed(self, value: int | float) -> None:
        if self._spin_box.value() != self._prev_value:
            self._prev_value = self._spin_box.value()
            self._config.set(self._cfg_key, value)
