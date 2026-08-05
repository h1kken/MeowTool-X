from __future__ import annotations

import typing as t

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget

import src.app.context as ctx
from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTInlineEditorStack, MTLabel, MTLabeledList, MTLineEdit, MTPlainLabel, MTWidget
from src.ui.widgets.settings import MTSwitchSetting
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.theme import files as theme_files
from src.utils.filesystem import FS, validate_filename

if t.TYPE_CHECKING:
    from src.config import Config


class SettingsThemePage(BasePage): # REWRITE THIS PAGE
    _OBJECT_NAME = 'Settings_Theme'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=obj_name)
        
        self._themes: dict[str, Path] = {}
        self._loaded_name = self._configured_name()

        FS.ensure_dir(PATH_THEMES_USER)
        
        self._build_ui()
        self._connect_signals()

        self._refresh(preferred=self._loaded_name)

    def _build_ui(
        self,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._main_content = MTWidget(obj_name=(*obj_name, 'Content'))
        self._main_content_layout = create_layout(LayoutType.HBOX, self._main_content)
        self._main_layout.addWidget(self._main_content)

        self._list_column = MTLabeledList(obj_name=obj_name)
        self._main_content_layout.addWidget(self._list_column)
        
        self._themes_list = self._list_column.list_widget
        
        self._actions_column = MTWidget(obj_name=(*obj_name, 'Actions_Column'))
        self._main_content_layout.addWidget(self._actions_column)

        self._build_actions_column(obj_name=obj_name)

    def _build_actions_column(
        self,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        self._actions_column_layout = create_layout(LayoutType.VBOX, self._actions_column)
        
        self._selected_value = self._add_info_row(tr_key='SLCTD', obj_name=(*obj_name, 'Selected'))
        self._loaded_value = self._add_info_row(tr_key='LDD', obj_name=(*obj_name, 'Loaded'))

        self._auto_load_row = MTSwitchSetting(config=self._config, tr_key='ATLD_SLCTD_CFG', obj_name=(*obj_name, 'Autoload'))
        self._actions_column_layout.addWidget(self._auto_load_row)
        
        self._load_button = MTButton(tr_key='LOAD', obj_name=(*obj_name, 'Apply'))
        self._actions_column_layout.addWidget(self._load_button)
        
        self._create_stack = self._build_inline_editor('Create', tr_key='CREATE', obj_name=obj_name)
        self._actions_column_layout.addWidget(self._create_stack)
        
        self._rename_stack = self._build_inline_editor('Rename', tr_key='RENAME', obj_name=obj_name)
        self._actions_column_layout.addWidget(self._rename_stack)

        self._delete_stack = self._delete_stack_widget()
        self._actions_column_layout.addWidget(self._delete_stack)

        self._open_location_button = MTButton(tr_key='OPN_FL_LCTN', obj_name=(*obj_name, 'Open_Location'))
        self._actions_column_layout.addWidget(self._open_location_button)

    def _connect_signals(self) -> None:
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_THEMES_USER))
        self._watcher.directoryChanged.connect(self._queue_refresh)

        self._refresh_timer = QTimer(self, singleShot=True, interval=CONFIGS_REFRESH_DEBOUNCE_MS)
        self._refresh_timer.timeout.connect(self._refresh)
        self._themes_list.currentItemChanged.connect(self._sync_actions)
        
        self._load_button.clicked.connect(self._load)
        
        self._create_button.clicked.connect(self._start_create)
        self._create_line_edit.returnPressed.connect(self._create)
        self._create_cancel_button.clicked.connect(self._cancel_create)
        
        self._rename_button.clicked.connect(self._start_rename)
        self._rename_line_edit.returnPressed.connect(self._rename)
        self._rename_cancel_button.clicked.connect(self._cancel_rename)
        
        self._delete_button.clicked.connect(self._confirm_delete)
        self._delete_confirm.clicked.connect(self._delete)
        self._delete_cancel.clicked.connect(self._cancel_delete)
        
        self._open_location_button.clicked.connect(self._open_location)
        self._config.configLoaded.connect(self._config_loaded)

    def _add_info_row(
        self,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> MTPlainLabel:
        row = MTWidget(obj_name=(*obj_name, 'Info'))
        row_layout = create_layout(LayoutType.HBOX, row)
        self._actions_column_layout.addWidget(row)
        
        label = MTLabel(tr_key=tr_key, obj_name=(*obj_name, 'Label'))
        row_layout.addWidget(label)
        
        value = MTPlainLabel(text='-', obj_name=(*obj_name, 'Value'))
        row_layout.addWidget(value, stretch=1)
        
        return value

    def _build_inline_editor(
        self,
        mode: str,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> MTInlineEditorStack:        
        stack = MTInlineEditorStack(obj_name=(*obj_name, mode))
        
        button = MTButton(tr_key=tr_key, obj_name=(*obj_name, mode))
        stack.addWidget(button)

        row = MTWidget(obj_name=(*obj_name, mode, 'Editor_Row'))
        row_layout = create_layout(LayoutType.HBOX, row)
        stack.addWidget(row)
        
        line_edit = MTLineEdit(obj_name=(*obj_name, mode, 'Editor'))
        row_layout.addWidget(line_edit, 1)
        
        cancel_button = MTButton(obj_name=(*obj_name, mode, 'Editor_Cancel'))
        # cancel.set_icon()
        row_layout.addWidget(cancel_button)

        match mode:
            case 'Create':
                self._create_button = button
                self._create_line_edit = line_edit
                self._create_cancel_button = cancel_button
            case 'Rename':
                self._rename_button = button
                self._rename_line_edit = line_edit
                self._rename_cancel_button = cancel_button
            case _:
                    raise ValueError(f'Unsupported inline editor mode: {mode}')
        
        return stack

    def _delete_stack_widget(
        self,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> MTInlineEditorStack:
        stack = MTInlineEditorStack()
        stack.setObjectName('Theme_Delete_Stack')
        
        self._delete_button = MTButton(tr_key='DELETE', obj_name=(*obj_name, 'Delete'))
        stack.addWidget(self._delete_button)
        
        row = MTWidget(obj_name=(*obj_name, 'Delete_Confirm_Row'))
        row_layout = create_layout(LayoutType.HBOX, row)
        stack.addWidget(row)
        
        self._delete_confirm = MTButton(tr_key='CONFIRM', obj_name=(*obj_name, 'Delete_Confirm'))
        row_layout.addWidget(self._delete_confirm, 1)
        
        self._delete_cancel = MTButton(tr_key='✕', obj_name=(*obj_name, 'Delete_Cancel'))
        row_layout.addWidget(self._delete_cancel)
        
        return stack

    def _configured_name(self) -> str:
        value = self._config.get('General>Theme')
        return str(value) or PATH_DEFAULT_THEME.stem

    def _refresh(self, *, preferred: str | None = None) -> None:
        themes: dict[str, Path] = {}
        for directory in (PATH_THEMES_SRC, PATH_THEMES_USER):
            for path in theme_files.iter_files(directory):
                themes[path.stem] = path
        self._themes = themes

        names = sorted(themes, key=str.casefold)
        selected = preferred if preferred in themes else None
        if selected is None and self._list_column.current_value() in themes:
            selected = self._list_column.current_value()
        if selected is None and names:
            selected = names[0]

        with QSignalBlocker(self._themes_list):
            self._list_column.set_items(names, preferred=selected)
        self._sync_actions()

    def _queue_refresh(self, _path: str) -> None:
        self._refresh_timer.start()

    def _selected_name(self) -> str | None:
        return self._list_column.current_value()

    def _selected_path(self) -> Path | None:
        name = self._selected_name()
        return self._themes.get(name) if name else None

    def _is_user_theme(self, path: Path | None) -> bool:
        if path is None:
            return False
        try:
            path.resolve().relative_to(PATH_THEMES_USER.resolve())
            return True
        except ValueError:
            return False

    def _sync_actions(self, *_args: object) -> None:
        selected = self._selected_name()
        
        user_theme = self._is_user_theme(self._selected_path())
        self._selected_value.setText(selected or '-')
        self._loaded_value.setText(self._loaded_name or '-')
        self._load_button.setEnabled(selected is not None)
        self._rename_stack.setEnabled(user_theme)
        self._delete_stack.setEnabled(user_theme)
        self._open_location_button.setEnabled(selected is not None)
        if not user_theme:
            self._cancel_rename()
            self._cancel_delete()

    def _load(self, name: str | None) -> None:
        name = name or self._selected_name()
        if name is None:
            return
        
        path = ctx.services.theme_manager.load(name)
        if path is None:
            return
        
        self._loaded_name = path.stem
        self._config.set('General>Theme', path.stem)
        self._sync_actions()

    def _load_selected(self) -> None:
        name = self._selected_name()
        if name:
            self._load(name)

    def _start_create(self) -> None:
        self._create_line_edit.clear()
        self._create_stack.setCurrentIndex(1)
        self._create_line_edit.setFocus()

    def _cancel_create(self) -> None:
        self._create_line_edit.clear()
        self._create_stack.setCurrentIndex(0)

    def _create(self) -> None:
        name = validate_filename(self._create_line_edit.text())
        if name is None or theme_files.find(PATH_THEMES_USER, name) is not None:
            return
        path = theme_files.output_path(PATH_THEMES_USER, name)
        selected = self._selected_path()
        payload: dict[str, t.Any] = (
            theme_files.read_safe(selected)
            if selected is not None
            else {'widgets': []}
        )
        try:
            theme_files.write(path, payload)
        except OSError:
            return
        self._cancel_create()
        self._refresh(preferred=name)

    def _start_rename(self) -> None:
        name = self._selected_name()
        if not name or not self._is_user_theme(self._selected_path()):
            return
        self._rename_line_edit.setText(name)
        self._rename_stack.setCurrentIndex(1)
        self._rename_line_edit.setFocus()
        self._rename_line_edit.selectAll()

    def _cancel_rename(self) -> None:
        self._rename_line_edit.clear()
        self._rename_stack.setCurrentIndex(0)

    def _rename(self) -> None:
        old_name = self._selected_name()
        old_path = self._selected_path()
        new_name = validate_filename(self._rename_line_edit.text())
        if (
            old_name is None
            or old_path is None
            or not self._is_user_theme(old_path)
            or not new_name
            or new_name == old_name
            or theme_files.find(PATH_THEMES_USER, new_name) is not None
        ):
            return

        new_path = theme_files.output_path(
            PATH_THEMES_USER,
            new_name,
            preferred_suffix=old_path.suffix,
        )
        try:
            old_path.rename(new_path)
        except OSError:
            return

        if self._loaded_name == old_name:
            self._load(new_name)
        self._cancel_rename()
        self._refresh(preferred=new_name)

    def _confirm_delete(self) -> None:
        if self._is_user_theme(self._selected_path()):
            self._delete_stack.setCurrentIndex(1)

    def _cancel_delete(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _delete(self) -> None:
        name = self._selected_name()
        path = self._selected_path()
        if name is None or path is None or not self._is_user_theme(path):
            return
        try:
            path.unlink()
        except OSError:
            return
        if self._loaded_name == name:
            self._load(PATH_DEFAULT_THEME.stem)
        self._cancel_delete()
        self._refresh(preferred=self._loaded_name)

    def _open_location(self) -> None:
        path = self._selected_path()
        if path is None or not path.exists():
            self._refresh()
            return
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _config_loaded(self) -> None:
        self._loaded_name = self._configured_name()
        self._refresh(preferred=self._loaded_name)
