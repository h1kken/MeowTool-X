from __future__ import annotations

import typing as t

from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QWidget

from src.translation import TranslationKey as TrKey
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.settings.base import MTBaseSetting
from src.ui.widgets.types import WidgetDataMap
from src.ui.widgets.common import MTSwitch, MTWidget, MTButton, MTLabel, MTLineEdit, MTPopup
from src.ui.widgets.settings import MTSwitchSetting

from src.config.defaults import SORT_KEYS, default_config
from src.config.types import SortCategoryKind
from src.services.roblox.constants import ROBLOX_COOKIE_CHECKER_MAIN_FIELDS
from src.utils.conversion import as_dict

if t.TYPE_CHECKING:
    from src.config import Config, ConfigLoader


def _sort_defaults() -> WidgetDataMap:
    root = as_dict(default_config()) or {}
    roblox = as_dict(root.get('Roblox')) or {}
    cookie_checker = as_dict(roblox.get('Cookie Checker')) or {}
    sorting = as_dict(cookie_checker.get('Sorting')) or {}
    categories = as_dict(sorting.get('Categories')) or {}
    return categories


_COOKIE_CHECKER_SORT_DEFAULTS: WidgetDataMap = _sort_defaults()
_COOKIE_CHECKER_SORT_TEXT_FLAGS: dict[str, dict[str, str]] = {
    'Gamepasses': {
        'Names': 'Gamepass Names',
        'Places': 'Place Names',
    },
    'Custom Gamepasses': {
        'Names': 'Gamepass Names',
        'Places': 'Place Names',
    },
    'Badges': {
        'Names': 'Badge Names',
        'Places': 'Place Names',
    },
    'Favorite Places': {
        'Names': 'Place Names',
    },
    'Bundles': {
        'Names': 'Bundle Names',
    },
    'Groups Owned': {
        'Names': 'Group Names',
    },
    'Roblox Badges': {
        'Names': 'Badge Names',
    },
}


class _BoundSwitchRow(MTBaseSetting[bool]):
    checked = Signal(bool)

    _OBJECT_NAME = 'Switch'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        text: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key, obj_name=(*obj_name, _BoundSwitchRow._OBJECT_NAME))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._suspend_config_write = False

        self._build_ui(text=text)
        self._connect_signals()

    def _build_ui(
        self,
        *,
        text: str = '',
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._label = MTLabel(obj_name=(obj_name,))
        self._label.setText(str(text))
        self._main_layout.addWidget(self._label)

        self._main_layout.addStretch()

        self._switch = MTSwitch(obj_name=(obj_name,))
        self._switch.setChecked(self._config.get(self._cfg_key, bool))
        self._main_layout.addWidget(self._switch)

    def _connect_signals(self) -> None:
        self._switch.toggled.connect(self._on_switch_toggled)
        self._config.configLoaded.connect(self.reload_from_config)

    def reload_from_config(self) -> None:
        self.set_checked(self._config.get(self._cfg_key, bool))

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
        self.checked.emit(bool(checked))

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


class _SortActionButton(MTButton): # TODO: remove this later
    rightClicked = Signal(bool)
    
    _DEFAULT_ICON_SOURCE = 'src/assets/icons/sort.svg'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, checkable=True, obj_name=obj_name)

    def nextCheckState(self) -> None:
        # Left click should open the popup, not mutate the persisted enabled state.
        return

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            point = event.position().toPoint()
            if self.rect().contains(point) and self.isEnabled():
                next_value = not self.isChecked()
                self.setChecked(next_value)
                self.rightClicked.emit(next_value)
                event.accept()
                return
        super().mouseReleaseEvent(event)


class _SortListEntryRow(MTWidget):
    changed = Signal()
    remove_requested = Signal(QWidget)

    _OBJECT_NAME = 'Sort_List_Entry_Row'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
        range_mode: bool,
        start_value: str = '',
        end_value: str = '',
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, _SortListEntryRow._OBJECT_NAME))
        
        self._range_mode = bool(range_mode)

        self._main_layout = create_layout(LayoutType.HBOX, self)

        self._start_edit = MTLineEdit(obj_name=(*obj_name, 'Start'))
        self._start_edit.setPlaceholderText('From')
        self._start_edit.setText(str(start_value).strip())
        self._main_layout.addWidget(self._start_edit, 1)

        self._end_edit: MTLineEdit | None = None
        if self._range_mode:
            self._end_edit = MTLineEdit(obj_name=(*obj_name, 'End'))
            self._end_edit.setPlaceholderText('To')
            self._end_edit.setText(str(end_value).strip())
            self._main_layout.addWidget(self._end_edit, 1)

        self._remove_button = MTButton(obj_name=(*obj_name, 'Remove'))
        self._remove_button.setText('X')
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

        end_text = self._end_edit.text().strip() if self._end_edit is not None else ''
        if not end_text:
            return None
        return f'{start_text}..{end_text}'


class _SortListEditor(MTWidget):
    changed = Signal()

    _OBJECT_NAME = 'Sort_List_Editor'

    def __init__(
        self,
        *,
        config: Config | ConfigLoader,
        text: str,
        cfg_key_enabled: str,
        cfg_key_items: str,
        obj_name: tuple[str, ...] = (),
        range_mode: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, _SortListEditor._OBJECT_NAME))
        
        self._config = config
        self._cfg_key_enabled = cfg_key_enabled
        self._cfg_key_items = cfg_key_items
        self._range_mode = range_mode
        self._entry_rows: list[_SortListEntryRow] = []
        self._suspend_save = False

        self._build_ui(text=text)

        self.reload_from_config()

    def _build_ui(
        self,
        *,
        text: str = '',
    ) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._enabled_row = _BoundSwitchRow(config=self._config, text=text, cfg_key=self._cfg_key_enabled, obj_name=(obj_name, 'Enabled'))
        self._main_layout.addWidget(self._enabled_row)

        self._entries_widget = MTWidget(obj_name=(obj_name, 'Entries'))
        self._entries_layout = create_layout(LayoutType.VBOX, self._entries_widget)
        self._main_layout.addWidget(self._entries_widget)

        self._add_button = MTButton(obj_name=(obj_name, 'Add'))
        self._main_layout.addWidget(self._add_button)

    def _connect_signals(self) -> None:
        self._enabled_row.checked.connect(self._sync_enabled_state)
        self._enabled_row.checked.connect(self._on_enabled_row_toggled)
        self._add_button.clicked.connect(self._add_empty_entry)
        self._config.configLoaded.connect(self.reload_from_config)

    def reload_from_config(self) -> None:
        enabled = self._config.get(self._cfg_key_enabled, bool)
        self._enabled_row.set_checked(enabled)
        items = as_dict(self._config.get(self._cfg_key_items, dict[str, t.Any])) or {}
        self._rebuild_entries({str(key): bool(value) for key, value in items.items()})
        self._sync_enabled_state()

    def _on_enabled_row_toggled(self, _: bool) -> None:
        self.changed.emit()

    def _sync_enabled_state(self, _: bool | None = None) -> None:
        enabled = self._enabled_row.is_checked()
        self._entries_widget.setEnabled(enabled)
        self._add_button.setEnabled(enabled)

    def _add_empty_entry(self) -> None:
        self._append_entry_row('', '')
        self._save_entries()

    def _append_entry_row(self, start_value: str, end_value: str) -> None:
        row = _SortListEntryRow(
            obj_name=(self.objectName(), str(len(self._entry_rows))),
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
                self._append_entry_row('', '')
                return

            for key in keys:
                if not self._range_mode:
                    self._append_entry_row(key, '')
                    continue

                start_value, end_value = self._split_range_key(key)
                self._append_entry_row(start_value, end_value)
        finally:
            self._suspend_save = False

    @staticmethod
    def _split_range_key(value: str) -> tuple[str, str]:
        normalized = str(value).strip()
        for separator in ('..', '->', '-', ':'):
            if separator not in normalized:
                continue
            left, right = normalized.split(separator, 1)
            return left.strip(), right.strip()
        return normalized, ''

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
    enabledChanged = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
        field_name: str,
        sort_kind: SortCategoryKind,
    ) -> None:
        super().__init__(parent, obj_name=obj_name, close_on_outside_click=True)
        self._config = config
        self._field_name = field_name
        self._sort_kind = sort_kind
        self._category_defaults = deepcopy(as_dict(_COOKIE_CHECKER_SORT_DEFAULTS.get(field_name)) or {})

        self._header = MTWidget(obj_name=(*obj_name, 'Header'))
        self._header_layout = create_layout(LayoutType.HBOX, self._header)

        self._title = MTLabel(tr=tr, obj_name=(*obj_name, 'Title'))

        self._close_button = MTButton(self._header, obj_name=(*obj_name, 'Close_Button'))
        self._close_button.setText('X')

        self._header_layout.addWidget(self._title)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._close_button)
        self.add_widget(self._header)

        self._enabled_row = _BoundSwitchRow(
            config=self._config,
            text='Sort',
            cfg_key=self._category_key('Enabled'),
            obj_name=(*obj_name, 'Enabled'),
        )
        self.add_widget(self._enabled_row)

        self._detail_widgets: list[_BoundSwitchRow | _SortListEditor] = []
        self._build_detail_widgets(obj_name)

        self._enabled_row.checked.connect(self._sync_enabled_state)
        self._enabled_row.checked.connect(self._on_enabled_toggled)
        self._enabled_row.checked.connect(self.enabledChanged.emit)
        self._close_button.clicked.connect(self.hide)
        self._config.configLoaded.connect(self.reload_from_config)

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
        return f'Roblox>Cookie Checker>Sorting>Categories>{self._field_name}>{suffix}'

    def _build_detail_widgets(self, obj_name: tuple[str, ...] = ()) -> None:
        if self._sort_kind != 'number':
            return

        self._zero_row = _BoundSwitchRow(
            config=self._config,
            text='Zero',
            cfg_key=self._category_key('Options>Zero'),
            obj_name=(*obj_name, 'Zero'),
        )
        self.add_widget(self._zero_row)
        self._detail_widgets.append(self._zero_row)

        self._from_editor = _SortListEditor(
            config=self._config,
            text='From',
            cfg_key_enabled=self._category_key('Options>From>Enabled'),
            cfg_key_items=self._category_key('Options>From>Items'),
            obj_name=(*obj_name, 'From'),
            range_mode=False,
        )
        self.add_widget(self._from_editor)
        self._detail_widgets.append(self._from_editor)

        self._from_to_editor = _SortListEditor(
            config=self._config,
            text='From To',
            cfg_key_enabled=self._category_key('Options>From To>Enabled'),
            cfg_key_items=self._category_key('Options>From To>Items'),
            obj_name=(*obj_name, 'From_To'),
            range_mode=True,
        )
        self.add_widget(self._from_to_editor)
        self._detail_widgets.append(self._from_to_editor)

        for option_key, label_text in _COOKIE_CHECKER_SORT_TEXT_FLAGS.get(
            self._field_name, {}
        ).items():
            row = _BoundSwitchRow(
                config=self._config,
                text=label_text,
                cfg_key=self._category_key(option_key),
                obj_name=(*obj_name, option_key),
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
            if self._config.get(f'Roblox>Cookie Checker>Sorting>Categories>{field}>Enabled', bool):
                is_enabled = True
                break
        self._config.set('Roblox>Cookie Checker>Sorting>Enabled', is_enabled)


class MTCookieCheckerFieldSetting(MTSwitchSetting):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config | ConfigLoader,
        cfg_key: str,
        tr: TrKey = TrKey(),
        obj_name: tuple[str, ...] = (),
        field_name: str,
    ) -> None:
        super().__init__(parent, config=config, cfg_key=cfg_key, tr=tr, obj_name=obj_name)
        
        self._field_name = field_name
        self._sort_kind: SortCategoryKind = SORT_KEYS.get(field_name, 'none')
        self._sort_enabled_cfg_key = f'Roblox>Cookie Checker>Sorting>Categories>{self._field_name}>Enabled'
        self._sort_popup: _CookieCheckerSortPopup | None = None
        self._sort_button: _SortActionButton | None = None

        if self._sort_kind != 'none':
            self._sort_button = _SortActionButton(self, obj_name=(*obj_name, 'Sort'))
            switch_index = self._main_layout.indexOf(self._switch)
            self._main_layout.insertWidget(max(0, switch_index), self._sort_button)

            self._sort_popup = _CookieCheckerSortPopup(
                self.window(),
                config=self._config,
                tr=tr,
                obj_name=(self.objectName(), 'Sort'),
                field_name=field_name,
                sort_kind=self._sort_kind,
            )
            self._apply_sort_popup_modal_host()
            self._sort_button.clicked.connect(self._toggle_sort_popup)
            self._sort_button.rightClicked.connect(self._toggle_sort_enabled)
            self._sort_popup.enabledChanged.connect(self._on_sort_enabled_changed)
            self._config.configLoaded.connect(self._sync_sort_button_state)
            self._config.valueChanged.connect(self._on_config_value_changed)
            self._sync_sort_button_state()

    def _apply_sort_popup_modal_host(self) -> None:
        if self._sort_popup is None:
            return
        parent_window = self.window()
        if parent_window is self:
            return
        modal_host = getattr(t.cast(t.Any, parent_window), '_popup_modal_host', None)
        if isinstance(modal_host, QWidget):
            self._sort_popup.set_modal_host(modal_host)

    def _sync_sort_button_state(self, *_args: object) -> None:
        if self._sort_button is None:
            return
        self._sort_button.setChecked(self._config.get(self._sort_enabled_cfg_key, bool))

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
        if self._sort_kind == 'none' or self._sort_popup is None:
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
