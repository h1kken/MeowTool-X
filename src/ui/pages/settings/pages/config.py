from __future__ import annotations

import typing as t

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLayout, QWidget, QSizePolicy, QStackedWidget

from src.app.paths import PATH_CONFIGS, PATH_DEFAULT_CONFIG
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTInlineEditorStack, MTLabel, MTLabeledList, MTLineEdit, MTPlainLabel, MTWidget
from src.ui.widgets.settings import MTSwitchRowSetting
from src.config import ConfigLoaderKey as CLKey
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.utils.filesystem import FS
from src.utils.filesystem.constants import FILENAME_SPECIAL_CHARS

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsConfigPage(BasePage):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: str = '',
    ):
        super().__init__(parent, config=config, obj_name=obj_name)

        FS.ensure_dir(PATH_CONFIGS)
        
        self._build_ui()
        self._connect_signals()
        
        self._refresh_configs(preferred=self._config.name)

    def _build_ui(self) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._autoload_name = self._read_autoload_name()

        self._main_content = MTWidget(obj_name='Config_Page_Widget')
        self._main_layout.addWidget(self._main_content)

        self._body_layout = create_layout(LayoutType.HBOX, self._main_content)

        self._list_column = MTLabeledList(obj_name='Config_List_Column')
        self._configs_list = self._list_column.list_widget
        self._actions_column = MTWidget(obj_name='Config_Actions_Column')

        self._build_actions_column()
        
        self._body_layout.addWidget(self._list_column, stretch=1)
        self._body_layout.addWidget(self._actions_column, stretch=1)

    def _connect_signals(self) -> None:
        self._refresh_timer = QTimer(self, singleShot=True, interval=CONFIGS_REFRESH_DEBOUNCE_MS)
        self._refresh_timer.timeout.connect(self._refresh_configs)
        
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_CONFIGS))
        self._watcher.directoryChanged.connect(self._on_configs_dir_changed)

        self._configs_list.currentItemChanged.connect(self._on_selection_changed)
        self._auto_load_row.switch.toggled.connect(self._on_auto_load_toggled)
        self._auto_save_row.switch.toggled.connect(self._on_auto_save_toggled)

        self._load_button.clicked.connect(self._load_selected_config)
        self._save_button.clicked.connect(self._save_selected_config)
        self._open_location_button.clicked.connect(self._open_selected_location)
        
        self._create_button.clicked.connect(self._start_create_edit)
        self._create_edit_line.returnPressed.connect(self._submit_create_edit)
        self._create_edit_cancel_button.clicked.connect(self._cancel_create_edit)
        
        self._rename_button.clicked.connect(self._start_rename_edit)
        self._rename_edit_line.returnPressed.connect(self._submit_rename_edit)
        self._rename_edit_cancel_button.clicked.connect(self._cancel_rename_edit)
        
        self._delete_button.clicked.connect(self._start_delete_confirm)
        self._delete_confirm_button.clicked.connect(self._delete_selected_config)
        self._delete_cancel_button.clicked.connect(self._cancel_delete_confirm)

        self._config.configLoaded.connect(self._on_config_loaded)

    def _build_actions_column(self) -> None:
        layout = create_layout(LayoutType.VBOX, self._actions_column)

        self._selected_value = self._add_info_row(layout, tr_key='SLCTD', obj_name='Config_Selected')
        self._loaded_value = self._add_info_row(layout, tr_key='LDD', obj_name='Config_Loaded')

        self._auto_load_row = MTSwitchRowSetting(tr_key='ATLD_SLCTD_CFG', obj_name='Config_Autoload')
        self._auto_save_row = MTSwitchRowSetting(tr_key='AT_SV_CFG_CHNGS', obj_name='Config_Auto_Save')

        self._load_button = MTButton(tr_key='LOAD', obj_name='Config_Load_Button')
        self._save_button = MTButton(tr_key='SAVE', obj_name='Config_Save_Button')
        self._rename_stack = self._build_inline_editor(mode='rename', tr_key='RENAME', obj_name='Config_Rename')
        self._create_stack = self._build_inline_editor(mode='create', tr_key='CREATE', obj_name='Config_Create')
        self._delete_stack = self._build_delete_confirm_stack(obj_name='Config_Delete')
        self._open_location_button = MTButton(tr_key='OPN_FL_LCTN', obj_name='Config_Open_Location_Button')
        
        layout.addWidget(self._auto_load_row)
        layout.addWidget(self._auto_save_row)
        layout.addWidget(self._load_button)
        layout.addWidget(self._save_button)
        layout.addWidget(self._rename_stack)
        layout.addWidget(self._create_stack)
        layout.addWidget(self._delete_stack)
        layout.addWidget(self._open_location_button)
        layout.addStretch()

    def _build_inline_editor(
        self,
        *,
        mode: str,
        tr_key: str,
        obj_name: str,
    ) -> QStackedWidget:
        stack = MTInlineEditorStack()
        stack.setObjectName(f'{obj_name}_Stack')
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        button = MTButton(tr_key=tr_key, obj_name=f'{obj_name}_Button')
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        editor_row = MTWidget(obj_name=f'{obj_name}_Editor_Row')
        editor_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        editor_layout = create_layout(LayoutType.HBOX, editor_row)
        
        line_edit = MTLineEdit(obj_name=f'{obj_name}_Editor_LineEdit')
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        cancel_btn = MTButton(tr_key='✕', obj_name=f'{obj_name}_Editor_Cancel_Button')
        cancel_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        editor_layout.addWidget(line_edit, 1)
        editor_layout.addWidget(cancel_btn)
        stack.addWidget(button)
        stack.addWidget(editor_row)

        match mode:
            case 'create':
                self._create_button = button
                self._create_edit_line = line_edit
                self._create_edit_cancel_button = cancel_btn
            case 'rename':
                self._rename_button = button
                self._rename_edit_line = line_edit
                self._rename_edit_cancel_button = cancel_btn
            case _:
                raise ValueError(f'Unsupported inline editor mode: {mode}')

        stack.setCurrentIndex(0)
        return stack

    def _build_delete_confirm_stack(
        self,
        *,
        obj_name: str,
    ) -> QStackedWidget:
        stack = MTInlineEditorStack()
        stack.setObjectName(f'{obj_name}_Stack')
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._delete_button = MTButton(tr_key='DELETE', obj_name=f'{obj_name}_Button')
        self._delete_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stack.addWidget(self._delete_button)

        confirm_row = MTWidget(obj_name=f'{obj_name}_Confirm_Row')
        confirm_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        confirm_layout = create_layout(LayoutType.HBOX, confirm_row)
        
        self._delete_confirm_button = MTButton(tr_key='Confirm', obj_name=f'{obj_name}_Confirm_Button')
        self._delete_confirm_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self._delete_cancel_button = MTButton(tr_key='✕', obj_name=f'{obj_name}_Cancel_Button')
        self._delete_cancel_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        confirm_layout.addWidget(self._delete_confirm_button, 1)
        confirm_layout.addWidget(self._delete_cancel_button)
        stack.addWidget(confirm_row)
        stack.setCurrentIndex(0)
        return stack

    def _add_info_row(
        self,
        layout: QLayout,
        *,
        tr_key: str,
        obj_name: str,
    ) -> MTPlainLabel:
        row = MTWidget(obj_name=f'{obj_name}_Row')
        row_layout = create_layout(LayoutType.HBOX, row)
        
        label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Label')
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        value_label = MTPlainLabel(text='-', obj_name=f'{obj_name}_Value')
        value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        
        row_layout.addWidget(label)
        row_layout.addWidget(value_label, stretch=1)
        layout.addWidget(row)
        
        return value_label

    def _iter_config_names(self) -> list[str]:
        names: list[str] = []
        for file_path in PATH_CONFIGS.glob('*.txt'):
            if not file_path.is_file():
                continue
            stem = file_path.stem
            if not stem or stem.startswith('.'):
                continue
            names.append(stem)
        names.sort(key=str.casefold)
        return names

    def _current_selected_name(self) -> str | None:
        return self._list_column.current_value()

    def _selected_config_path(self) -> Path | None:
        selected = self._current_selected_name()
        if not selected:
            return None
        return PATH_CONFIGS / f'{selected}.txt'

    def _read_autoload_name(self) -> str:
        return str(self._config.loader.get(CLKey.LOADER_CONFIG_ON_LOAD)).strip() or PATH_DEFAULT_CONFIG.stem

    def _set_autoload_name(self, value: str) -> str:
        normalized = str(value).strip() or PATH_DEFAULT_CONFIG.stem
        if normalized == self._autoload_name:
            return self._autoload_name
        self._config.loader.set(CLKey.LOADER_CONFIG_ON_LOAD, normalized)
        self._autoload_name = normalized
        return normalized

    def _pick_target_name(
        self, names: list[str], preferred: str | None = None
    ) -> str | None:
        for candidate in (preferred, self._current_selected_name(), self._config.name):
            if candidate in names:
                return candidate
        return names[0] if names else None

    @staticmethod
    def _is_default_autoload_locked(selected: str | None, autoload: str) -> bool:
        return selected == autoload == PATH_DEFAULT_CONFIG.stem

    def _refresh_configs(self, *, preferred: str | None = None) -> None:
        names = self._iter_config_names()
        target = self._pick_target_name(names, preferred=preferred)
        
        with QSignalBlocker(self._configs_list):
            self._list_column.set_items(names, preferred=target)

        self._sync_actions_state()

    def _sync_actions_state(self) -> None:
        selected = self._current_selected_name()
        autoload = self._autoload_name
        loaded = self._config.name

        self._selected_value.setText(selected or '-')
        self._loaded_value.setText(loaded or '-')

        has_selection = selected is not None
        is_default_autoload_locked = self._is_default_autoload_locked(selected, autoload)
        self._load_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)
        self._delete_stack.setEnabled(has_selection)
        self._rename_button.setEnabled(has_selection)
        self._rename_stack.setEnabled(has_selection)
        self._open_location_button.setEnabled(has_selection)
        self._auto_load_row.switch.setEnabled(has_selection and not is_default_autoload_locked)
        self._save_button.setEnabled(has_selection)
        self._create_stack.setEnabled(True)

        if not has_selection:
            self._cancel_rename_edit()
            self._cancel_delete_confirm()

        with QSignalBlocker(self._auto_load_row.switch):
            self._auto_load_row.switch.setChecked(has_selection and selected == autoload)
        with QSignalBlocker(self._auto_save_row.switch):
            self._auto_save_row.switch.setChecked(bool(self._config.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES)))

    def _on_selection_changed(self, *_args: object) -> None:
        self._sync_actions_state()

    def _on_configs_dir_changed(self, _path: str) -> None:
        self._refresh_timer.start()

    def _on_auto_load_toggled(self, checked: bool) -> None:
        selected = self._current_selected_name()
        if not selected:
            return

        if not checked and self._is_default_autoload_locked(
            selected, self._autoload_name
        ):
            with QSignalBlocker(self._auto_load_row.switch):
                self._auto_load_row.switch.setChecked(True)
            self._sync_actions_state()
            return

        if checked:
            self._set_autoload_name(selected)
        elif self._autoload_name == selected:
            self._set_autoload_name(PATH_DEFAULT_CONFIG.stem)

        self._sync_actions_state()

    def _on_auto_save_toggled(self, checked: bool) -> None:
        self._config.loader.set(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, bool(checked))
        self._sync_actions_state()

    def _save_selected_config(self) -> None:
        selected = self._current_selected_name()
        if not selected:
            return
        if selected != self._config.name:
            self._config.load(selected)
        self._config.save()
        self._refresh_configs(preferred=selected)

    def _normalize_new_name(self, value: str) -> str:
        name = str(value).strip().removesuffix('.txt')
        if (
            not name
            or name.startswith('.')
            or any(char in name for char in FILENAME_SPECIAL_CHARS)
        ):
            return ''
        return name

    def _start_create_edit(self) -> None:
        self._create_edit_line.clear()
        self._create_stack.setCurrentIndex(1)
        self._create_edit_line.setFocus()

    def _cancel_create_edit(self) -> None:
        self._create_edit_line.clear()
        self._create_stack.setCurrentIndex(0)

    def _submit_create_edit(self) -> None:
        name = self._normalize_new_name(self._create_edit_line.text())
        if not name:
            return

        self._config.create_config(name)
        self._cancel_create_edit()
        self._refresh_configs(preferred=self._config.name)

    def _start_rename_edit(self) -> None:
        selected = self._current_selected_name()
        if not selected:
            return
        self._rename_edit_line.setText(selected)
        self._rename_stack.setCurrentIndex(1)
        self._rename_edit_line.setFocus()
        self._rename_edit_line.selectAll()

    def _cancel_rename_edit(self) -> None:
        self._rename_edit_line.clear()
        self._rename_stack.setCurrentIndex(0)

    def _start_delete_confirm(self) -> None:
        if not self._current_selected_name():
            return
        self._delete_stack.setCurrentIndex(1)

    def _cancel_delete_confirm(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _submit_rename_edit(self) -> None:
        selected = self._current_selected_name()
        if not selected:
            self._cancel_rename_edit()
            return
        new_name = self._normalize_new_name(self._rename_edit_line.text())
        if not new_name or not self._config.rename(selected, new_name):
            return

        if self._autoload_name == selected:
            self._set_autoload_name(new_name)

        self._cancel_rename_edit()
        self._refresh_configs(preferred=new_name)

    def _load_selected_config(self) -> None:
        selected = self._current_selected_name()
        if not selected:
            return
        self._config.load(selected)
        self._refresh_configs(preferred=selected)

    def _delete_selected_config(self) -> None:
        selected = self._current_selected_name()
        if not selected:
            self._cancel_delete_confirm()
            return

        if self._autoload_name == selected:
            self._set_autoload_name(PATH_DEFAULT_CONFIG.stem)

        self._cancel_delete_confirm()
        self._refresh_configs(preferred=self._config.name)

    def _open_selected_location(self) -> None:
        config_path = self._selected_config_path()
        if config_path is None:
            return
        if not config_path.exists():
            self._refresh_configs()
            return

        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', str(config_path)])
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(config_path).parent)))

    def _on_config_loaded(self) -> None:
        self._refresh_configs(preferred=self._config.name)
