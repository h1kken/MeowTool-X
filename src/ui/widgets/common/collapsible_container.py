from __future__ import annotations

import typing as t

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.app.paths import PATH_CONTAINER_ARROW_ICON
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTLabel, MTWidget
from src.ui.widgets.helpers import icon, repolish


class MTCollapsibleContainer(MTWidget):
    toggled = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: str = '',
        widgets: t.Sequence[QWidget] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f'{obj_name}_Container_Widget')

        self._default_toggle_arrow_source = str(PATH_CONTAINER_ARROW_ICON)
        self._default_toggle_arrow_size = _COLLAPSIBLE_TOGGLE_ICON_SIZE
        self._default_toggle_button_size = _COLLAPSIBLE_TOGGLE_BUTTON_SIZE
        self._default_toggle_arrow_color: str | None = None
        self._default_toggle_arrow_collapsed_rotation = 0.0
        self._default_toggle_arrow_expanded_rotation = 90.0
        
        self._reset_toggle_arrow_values()
        self._toggle_arrow_rotation = self._default_toggle_arrow_expanded_rotation
        self._content_height_animation_active = False

        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._header_widget = MTWidget(obj_name=f'{obj_name}_Container_Header_Widget')
        self._header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_layout = create_layout(LayoutType.HBOX, self._header_widget)
        self._header_separator = MTWidget(obj_name=f'{obj_name}_Container_Header_Separator')
        self._header_separator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._header_separator.setFixedHeight(1)
        self._header_separator.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Container_Header_Title')
        self._label.setCursor(Qt.CursorShape.PointingHandCursor)

        self._toggle_button = MTButton(
            obj_name=f'{obj_name}_Container_Header_Button',
            checkable=True,
            checked=True,
        )
        self._apply_toggle_button_metrics()
        self._content_widget = MTWidget(obj_name=f'{obj_name}_Container_Content_Widget')
        self._content_layout = create_layout(LayoutType.VBOX, self._content_widget)

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
        self.setProperty('expanded', initial_checked)
        self._header_widget.setProperty('expanded', initial_checked)
        self._toggle_button.setProperty('expanded', initial_checked)
        self._content_widget.setMaximumHeight(self._content_target_height())
        self._toggle_arrow_rotation = (
            self._toggle_arrow_expanded_rotation
            if initial_checked
            else self._toggle_arrow_collapsed_rotation
        )
        self._refresh_toggle_icon()

        self._toggle_button.toggled.connect(self._toggle_collapsed)
        self._toggle_button.toggled.connect(self.toggled.emit)

        if self._toggle_button.isChecked():
            self._sync_content_height_to_layout()

    def _toggle_collapsed(self, checked: bool) -> None:
        self.setProperty('expanded', checked)
        self._header_widget.setProperty('expanded', checked)
        self._toggle_button.setProperty('expanded', checked)

        if bool(self.property('_themeAnimatedContentHeight')):
            if checked:
                self._content_widget.setMaximumHeight(0)
                self._content_widget.setVisible(True)
                self._header_separator.setVisible(True)
        else:
            target_height = self._content_target_height() if checked else 0
            self.set_part_metric('content', ('height',), float(target_height))
        if bool(self.property('_themeAnimatedArrowRotation')):
            self._refresh_toggle_icon()
        else:
            target_rotation = (
                self._toggle_arrow_expanded_rotation
                if checked
                else self._toggle_arrow_collapsed_rotation
            )
            self.set_part_metric('icon', ('rotation',), target_rotation)
        repolish(self)
        repolish(self._header_widget)
        repolish(self._header_separator)
        repolish(self._toggle_button)

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

    def _reset_toggle_arrow_values(self) -> None:
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
        self._toggle_button.setIcon(self._current_toggle_icon(self._toggle_arrow_rotation))

    def _current_toggle_icon(self, rotation: float) -> QIcon:
        color = (
            self._toggle_arrow_color
            or self._toggle_button.palette()
            .buttonText()
            .color()
            .name(QColor.NameFormat.HexArgb)
        )
        return icon(self._toggle_arrow_source, color, rotation, self._toggle_arrow_size)

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
        if part == 'icon' and path and path[0] == 'rotation':
            return float(self._toggle_arrow_rotation)

        if part != 'content' or not path or path[0] not in {'height', 'size'}:
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
        if part == 'icon' and tokens and tokens[0] == 'rotation':
            self._toggle_arrow_rotation = float(value)
            self._refresh_toggle_icon()
            return True

        if part != 'content':
            return False

        if not tokens or tokens[0] not in {'height', 'size'}:
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
        if part == 'icon' and path and path[0] == 'rotation':
            return float(value)
        if part == 'content' and path and path[0] in {'height', 'size'}:
            target_height = self._content_target_height()
            resolved_value = max(0.0, float(value))
            if target_height > 0:
                resolved_value = min(resolved_value, float(target_height))
            return resolved_value
        return float(value)

    def handle_part_animation_state(
        self, part: str, path: tuple[str, ...], active: bool
    ) -> None:
        if part == 'content' and path and path[0] in {'height', 'size'}:
            self._content_height_animation_active = bool(active)
            if not active and self._toggle_button.isChecked():
                self._sync_content_height_to_layout()
