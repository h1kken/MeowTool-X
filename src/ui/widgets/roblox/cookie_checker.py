from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QWidget

from src.config.defaults import SORT_KEYS, default_config
from src.config.manager import Config
from src.config.types import SortCategoryKind
from src.theme.schema.access import theme_map
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets.types import WidgetThemeMap
from src.ui.widgets import (
    MTSwitch, MTWidget, MTButton,
    MTLabel, MTLineEdit, MTPopup,
    MTSwitchSetting,
)
from src.services.roblox.constants import ROBLOX_COOKIE_CHECKER_MAIN_FIELDS


def _sort_defaults() -> WidgetThemeMap:
    root = theme_map(default_config()) or {}
    roblox = theme_map(root.get("Roblox")) or {}
    cookie_checker = theme_map(roblox.get("Cookie Checker")) or {}
    sorting = theme_map(cookie_checker.get("Sorting")) or {}
    categories = theme_map(sorting.get("Categories")) or {}
    return categories


_COOKIE_CHECKER_SORT_DEFAULTS: WidgetThemeMap = _sort_defaults()
_COOKIE_CHECKER_SORT_TEXT_FLAGS: dict[str, dict[str, str]] = {
    "Gamepasses": {
        "Names": "Gamepass Names",
        "Places": "Place Names",
    },
    "Custom Gamepasses": {
        "Names": "Gamepass Names",
        "Places": "Place Names",
    },
    "Badges": {
        "Names": "Badge Names",
        "Places": "Place Names",
    },
    "Favorite Places": {
        "Names": "Place Names",
    },
    "Bundles": {
        "Names": "Bundle Names",
    },
    "Groups Owned": {
        "Names": "Group Names",
    },
    "Roblox Badges": {
        "Names": "Badge Names",
    },
}


class _BoundSwitchRow(MTWidget):
    toggled = Signal(bool)

    def __init__(
        self,
        *,
        config: Config,
        label_text: str,
        cfg_key: str,
        default: bool,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._cfg_key = cfg_key
        self._default = bool(default)
        self._suspend_config_write = False

        self.setObjectName(f"{obj_name}_Row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._label = MTLabel(tr_key="", obj_name=f"{obj_name}_Label")
        self._label.setText(str(label_text))
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self._switch = MTSwitch(obj_name=f"{obj_name}_Switch")
        self._switch.setChecked(
            bool(self._config.get(self._cfg_key, default=self._default))
        )

        self._main_layout.addWidget(self._label)
        self._main_layout.addStretch()
        self._main_layout.addWidget(self._switch)

        self._switch.toggled.connect(self._on_switch_toggled)
        self._config.config_loaded.connect(self.reload_from_config)

    def reload_from_config(self) -> None:
        self.set_checked(bool(self._config.get(self._cfg_key, default=self._default)))

    def set_checked(self, checked: bool) -> None:
        target = bool(checked)
        if self._switch.isChecked() == target:
            return

        self._suspend_config_write = True
        try:
            self._switch.setChecked(target)
        finally:
            self._suspend_config_write = False

    def is_checked(self) -> bool:
        return self._switch.isChecked()

    def _on_switch_toggled(self, checked: bool) -> None:
        if not self._suspend_config_write:
            self._config.set(self._cfg_key, bool(checked))
        self.toggled.emit(bool(checked))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        available_height = max(12, self.height())
        self._switch.sync_size(
            bounds_height=available_height - 2,
            bounds_width=max(1, self.width() // 3),
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)

        point = event.position().toPoint()
        if not self.rect().contains(point):
            return super().mouseReleaseEvent(event)

        child = self.childAt(point)
        if child is not None and (
            child is self._switch or self._switch.isAncestorOf(child)
        ):
            return super().mouseReleaseEvent(event)

        if self._switch.isEnabled():
            self._switch.setChecked(not self._switch.isChecked())
            event.accept()
            return

        super().mouseReleaseEvent(event)


class _SortActionButton(MTButton):
    right_clicked = Signal(bool)
    _DEFAULT_ICON_SOURCE = 'src/assets/icons/sort.svg'

    def __init__(
        self,
        *,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr_key="", checkable=True, obj_name=obj_name, parent=parent)
        self.setText("")
        self.set_text_icon(
            source=self._DEFAULT_ICON_SOURCE,
            align='left',
            size=QSize(14, 14),
            spacing=0.0,
        )

    def nextCheckState(self) -> None:
        # Left click should open the popup, not mutate the persisted enabled state.
        return

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            point = event.position().toPoint()
            if self.rect().contains(point) and self.isEnabled():
                next_value = not self.isChecked()
                self.setChecked(next_value)
                self.right_clicked.emit(next_value)
                event.accept()
                return
        super().mouseReleaseEvent(event)


class _SortListEntryRow(MTWidget):
    changed = Signal()
    remove_requested = Signal(QWidget)

    def __init__(
        self,
        *,
        obj_name: str,
        range_mode: bool,
        start_value: str = "",
        end_value: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._range_mode = bool(range_mode)
        self.setObjectName(f"{obj_name}_Entry_Row")

        self._main_layout = create_layout(LayoutType.HBOX, parent=self)

        self._start_edit = MTLineEdit(obj_name=f"{obj_name}_Start_LineEdit")
        self._start_edit.setPlaceholderText("From")
        self._start_edit.setText(str(start_value).strip())
        self._main_layout.addWidget(self._start_edit, 1)

        self._end_edit: MTLineEdit | None = None
        if self._range_mode:
            self._end_edit = MTLineEdit(obj_name=f"{obj_name}_End_LineEdit")
            self._end_edit.setPlaceholderText("To")
            self._end_edit.setText(str(end_value).strip())
            self._main_layout.addWidget(self._end_edit, 1)

        self._remove_button = MTButton(tr_key="", obj_name=f"{obj_name}_Remove_Button")
        self._remove_button.setText("X")
        self._main_layout.addWidget(self._remove_button)

        def _emit_text_changed(_: str) -> None:
            self.changed.emit()

        def _request_remove() -> None:
            self.remove_requested.emit(self)

        self._start_edit.editingFinished.connect(self.changed.emit)
        self._start_edit.textChanged.connect(_emit_text_changed)
        if self._end_edit is not None:
            self._end_edit.editingFinished.connect(self.changed.emit)
            self._end_edit.textChanged.connect(_emit_text_changed)
        self._remove_button.clicked.connect(_request_remove)

    def entry_key(self) -> str | None:
        start_text = self._start_edit.text().strip()
        if not start_text:
            return None

        if not self._range_mode:
            return start_text

        end_text = self._end_edit.text().strip() if self._end_edit is not None else ""
        if not end_text:
            return None
        return f"{start_text}..{end_text}"


class _SortListEditor(MTWidget):
    changed = Signal()

    def __init__(
        self,
        *,
        config: Config,
        label_text: str,
        cfg_key_enabled: str,
        cfg_key_items: str,
        obj_name: str,
        range_mode: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._cfg_key_enabled = cfg_key_enabled
        self._cfg_key_items = cfg_key_items
        self._range_mode = bool(range_mode)
        self._entry_rows: list[_SortListEntryRow] = []
        self._suspend_save = False

        self.setObjectName(f"{obj_name}_Editor")
        self._main_layout = create_layout(LayoutType.VBOX, parent=self)

        self._enabled_row = _BoundSwitchRow(
            config=self._config,
            label_text=label_text,
            cfg_key=self._cfg_key_enabled,
            default=False,
            obj_name=f"{obj_name}_Enabled",
        )
        self._main_layout.addWidget(self._enabled_row)

        self._entries_widget = MTWidget(obj_name=f"{obj_name}_Entries_Widget")
        self._entries_layout = create_layout(LayoutType.VBOX, parent=self._entries_widget)
        self._main_layout.addWidget(self._entries_widget)

        self._add_button = MTButton(tr_key="", obj_name=f"{obj_name}_Add_Button")
        self._add_button.setText("ADD")
        self._main_layout.addWidget(self._add_button)

        self._enabled_row.toggled.connect(self._sync_enabled_state)
        self._enabled_row.toggled.connect(self._on_enabled_row_toggled)
        self._add_button.clicked.connect(self._add_empty_entry)
        self._config.config_loaded.connect(self.reload_from_config)

        self.reload_from_config()

    def reload_from_config(self) -> None:
        enabled = bool(self._config.get(self._cfg_key_enabled, default=False))
        self._enabled_row.set_checked(enabled)
        items = theme_map(self._config.get(self._cfg_key_items, default={})) or {}
        self._rebuild_entries({str(key): bool(value) for key, value in items.items()})
        self._sync_enabled_state()

    def _on_enabled_row_toggled(self, _: bool) -> None:
        self.changed.emit()

    def _sync_enabled_state(self, _: bool | None = None) -> None:
        enabled = self._enabled_row.is_checked()
        self._entries_widget.setEnabled(enabled)
        self._add_button.setEnabled(enabled)

    def _add_empty_entry(self) -> None:
        self._append_entry_row("", "")
        self._save_entries()

    def _append_entry_row(self, start_value: str, end_value: str) -> None:
        row = _SortListEntryRow(
            obj_name=f"{self.objectName()}_{len(self._entry_rows)}",
            range_mode=self._range_mode,
            start_value=start_value,
            end_value=end_value,
        )
        row.changed.connect(self._save_entries)
        row.remove_requested.connect(self._remove_entry_row)
        self._entry_rows.append(row)
        self._entries_layout.addWidget(row)

    def _remove_entry_row(self, row_widget: QWidget) -> None:
        self._entry_rows = [row for row in self._entry_rows if row is not row_widget]
        row_widget.setParent(None)
        row_widget.deleteLater()
        self._save_entries()

    def _rebuild_entries(self, items: dict[str, bool]) -> None:
        self._suspend_save = True
        try:
            for row in self._entry_rows:
                row.setParent(None)
                row.deleteLater()
            self._entry_rows.clear()

            keys = [str(key).strip() for key in items.keys() if str(key).strip()]
            if not keys:
                self._append_entry_row("", "")
                return

            for key in keys:
                if not self._range_mode:
                    self._append_entry_row(key, "")
                    continue

                start_value, end_value = self._split_range_key(key)
                self._append_entry_row(start_value, end_value)
        finally:
            self._suspend_save = False

    @staticmethod
    def _split_range_key(value: str) -> tuple[str, str]:
        normalized = str(value).strip()
        for separator in ("..", "->", "-", ":"):
            if separator not in normalized:
                continue
            left, right = normalized.split(separator, 1)
            return left.strip(), right.strip()
        return normalized, ""

    def _save_entries(self) -> None:
        if self._suspend_save:
            return

        items: dict[str, bool] = {}
        for row in self._entry_rows:
            entry_key = row.entry_key()
            if entry_key is None:
                continue
            items[entry_key] = True

        self._config.set(self._cfg_key_items, items)
        self.changed.emit()


class _CookieCheckerSortPopup(MTPopup):
    enabled_changed = Signal(bool)

    def __init__(
        self,
        *,
        config: Config,
        field_name: str,
        sort_kind: SortCategoryKind,
        tr_key: str,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(obj_name=obj_name, parent=parent, close_on_outside_click=True)
        self._config = config
        self._field_name = field_name
        self._sort_kind = sort_kind
        self._category_defaults = deepcopy(theme_map(_COOKIE_CHECKER_SORT_DEFAULTS.get(field_name)) or {})

        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._header = MTWidget(obj_name=f"{obj_name}_Header_Widget")
        self._header_layout = create_layout(LayoutType.HBOX, parent=self._header)

        self._title = MTLabel(tr_key=tr_key, obj_name=f"{obj_name}_Title")
        self._title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._close_button = MTButton(
            tr_key="",
            obj_name=f"{obj_name}_Close_Button",
            parent=self._header,
        )
        self._close_button.setText("X")

        self._header_layout.addWidget(self._title)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._close_button)
        self.add_widget(self._header)

        self._enabled_row = _BoundSwitchRow(
            config=self._config,
            label_text="Sort",
            cfg_key=self._category_key("Enabled"),
            default=bool(self._category_defaults.get("Enabled", False)),
            obj_name=f"{obj_name}_Enabled",
        )
        self.add_widget(self._enabled_row)

        self._detail_widgets: list[_BoundSwitchRow | _SortListEditor] = []
        self._build_detail_widgets(obj_name)

        self._enabled_row.toggled.connect(self._sync_enabled_state)
        self._enabled_row.toggled.connect(self._on_enabled_toggled)
        self._enabled_row.toggled.connect(self.enabled_changed.emit)
        self._close_button.clicked.connect(self.hide)
        self._config.config_loaded.connect(self.reload_from_config)

        self.reload_from_config()

    def _on_enabled_toggled(self, _: bool) -> None:
        self._sync_global_sorting_enabled()

    def reload_from_config(self) -> None:
        self._enabled_row.reload_from_config()
        for widget in self._detail_widgets:
            widget.reload_from_config()
        self._sync_enabled_state()

    def set_enabled_state(self, enabled: bool) -> None:
        self._enabled_row.set_checked(enabled)
        self._sync_enabled_state()

    def sync_enabled_state(self) -> None:
        self._sync_enabled_state()

    def _category_key(self, suffix: str) -> str:
        return f"Roblox>Cookie Checker>Sorting>Categories>{self._field_name}>{suffix}"

    def _build_detail_widgets(self, obj_name: str) -> None:
        options_defaults = theme_map(self._category_defaults.get("Options")) or {}
        if self._sort_kind != "number":
            return

        self._zero_row = _BoundSwitchRow(
            config=self._config,
            label_text="Zero",
            cfg_key=self._category_key("Options>Zero"),
            default=bool(options_defaults.get("Zero", False)),
            obj_name=f"{obj_name}_Zero",
        )
        self.add_widget(self._zero_row)
        self._detail_widgets.append(self._zero_row)

        self._from_editor = _SortListEditor(
            config=self._config,
            label_text="From",
            cfg_key_enabled=self._category_key("Options>From>Enabled"),
            cfg_key_items=self._category_key("Options>From>Items"),
            obj_name=f"{obj_name}_From",
            range_mode=False,
        )
        self.add_widget(self._from_editor)
        self._detail_widgets.append(self._from_editor)

        self._from_to_editor = _SortListEditor(
            config=self._config,
            label_text="From To",
            cfg_key_enabled=self._category_key("Options>From To>Enabled"),
            cfg_key_items=self._category_key("Options>From To>Items"),
            obj_name=f"{obj_name}_From_To",
            range_mode=True,
        )
        self.add_widget(self._from_to_editor)
        self._detail_widgets.append(self._from_to_editor)

        for option_key, label_text in _COOKIE_CHECKER_SORT_TEXT_FLAGS.get(
            self._field_name, {}
        ).items():
            row = _BoundSwitchRow(
                config=self._config,
                label_text=label_text,
                cfg_key=self._category_key(option_key),
                default=bool(self._category_defaults.get(option_key, False)),
                obj_name=f"{obj_name}_{option_key}",
            )
            self.add_widget(row)
            self._detail_widgets.append(row)

    def _sync_enabled_state(self, _: bool | None = None) -> None:
        enabled = self._enabled_row.is_checked()
        for widget in self._detail_widgets:
            widget.setEnabled(enabled)

    def _sync_global_sorting_enabled(self) -> None:
        is_enabled = False
        for field in ROBLOX_COOKIE_CHECKER_MAIN_FIELDS:
            if bool(
                self._config.get(
                    f"Roblox>Cookie Checker>Sorting>Categories>{field}>Enabled",
                    default=False,
                )
            ):
                is_enabled = True
                break
        self._config.set("Roblox>Cookie Checker>Sorting>Enabled", is_enabled)


class MTCookieCheckerFieldSetting(MTSwitchSetting):
    def __init__(
        self,
        *,
        config: Config,
        field_name: str,
        tr_key: str,
        cfg_key: str,
        default: bool,
        obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            config=config,
            tr_key=tr_key,
            cfg_key=cfg_key,
            default=default,
            obj_name=obj_name,
            parent=parent,
        )
        self._field_name = field_name
        self._sort_kind: SortCategoryKind = SORT_KEYS.get(field_name, "none")
        self._sort_enabled_cfg_key = f"Roblox>Cookie Checker>Sorting>Categories>{self._field_name}>Enabled"
        self._sort_popup: _CookieCheckerSortPopup | None = None
        self._sort_button: _SortActionButton | None = None

        if self._sort_kind != "none":
            self._sort_button = _SortActionButton(
                obj_name=f"{obj_name}_Sort_Button",
                parent=self,
            )
            switch_index = self._layout.indexOf(self._switch)
            self._layout.insertWidget(max(0, switch_index), self._sort_button)

            self._sort_popup = _CookieCheckerSortPopup(
                config=self._config,
                field_name=field_name,
                sort_kind=self._sort_kind,
                tr_key=tr_key,
                obj_name=f"{self.objectName()}_Sort_Popup",
                parent=self.window(),
            )
            self._apply_sort_popup_modal_host()
            self._sort_button.clicked.connect(self._toggle_sort_popup)
            self._sort_button.right_clicked.connect(self._toggle_sort_enabled)
            self._sort_popup.enabled_changed.connect(self._on_sort_enabled_changed)
            self._config.config_loaded.connect(self._sync_sort_button_state)
            self._config.value_changed.connect(self._on_config_value_changed)
            self._sync_sort_button_state()

    def _apply_sort_popup_modal_host(self) -> None:
        if self._sort_popup is None:
            return
        parent_window = self.window()
        if parent_window is self:
            return
        modal_host = getattr(cast(Any, parent_window), "_popup_modal_host", None)
        if isinstance(modal_host, QWidget):
            self._sort_popup.set_modal_host(modal_host)

    def _sync_sort_button_state(self, *_args: object) -> None:
        if self._sort_button is None:
            return
        self._sort_button.setChecked(
            bool(self._config.get(self._sort_enabled_cfg_key, default=False))
        )

    def _on_config_value_changed(self, key: str, value: object) -> None:
        if str(key).strip() == self._sort_enabled_cfg_key:
            if self._sort_button is not None:
                self._sort_button.setChecked(bool(value))
            if self._sort_popup is not None and self._sort_popup.isVisible():
                self._sort_popup.set_enabled_state(bool(value))

    def _on_sort_enabled_changed(self, enabled: bool) -> None:
        if self._sort_button is not None:
            self._sort_button.setChecked(bool(enabled))

    def _toggle_sort_enabled(self, enabled: bool) -> None:
        self._config.set(self._sort_enabled_cfg_key, bool(enabled))
        if self._sort_popup is not None and self._sort_popup.isVisible():
            self._sort_popup.set_enabled_state(bool(enabled))

    def _toggle_sort_popup(self) -> None:
        if self._sort_kind == "none" or self._sort_popup is None:
            return

        if self._sort_popup.isVisible():
            self._sort_popup.hide()
            return

        self._apply_sort_popup_modal_host()
        self._sort_popup.show_centered()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.rect().contains(point):
                child = self.childAt(point)
                if self._sort_button is not None and child is not None and (
                    child is self._sort_button or self._sort_button.isAncestorOf(child)
                ):
                    return MTWidget.mouseReleaseEvent(self, event)
        super().mouseReleaseEvent(event)


__all__ = ["MTCookieCheckerFieldSetting"]
