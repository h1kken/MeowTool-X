from __future__ import annotations

import typing as t

import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget

import src.app.context as ctx
from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTInlineStackedWidget, MTLabel, MTLineEdit, MTList, MTPlainLabel, MTWidget
from src.ui.widgets.settings import MTSwitchSetting
from src.config import ConfigKey as CKey
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.utils.filesystem import FS

if t.TYPE_CHECKING:
    from src.config import Config
    from src.ui.widgets.common.list import MTListItem


class SettingsThemePage(BasePage):
    _OBJECT_NAME = 'Theme'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ):
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsThemePage._OBJECT_NAME))
        
        self._autoload_name = str(self._config.get(CKey.GENERAL_THEME)).strip()
        self._selected_name = self._autoload_name
        
        self._build_ui()
        self._connect_signals()

        self._refresh_themes()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)
        
        self._content_widget = MTWidget(obj_name=(obj_name, 'Content'))
        self._content_layout = create_layout(LayoutType.HBOX, self._content_widget)
        self._main_layout.addWidget(self._content_widget)

        self._themes_list_widget = MTList(obj_name=(obj_name,))
        self._content_layout.addWidget(self._themes_list_widget)
        
        self._action_columns_widget = MTWidget(obj_name=(obj_name, 'Actions_Column'))
        self._actions_column_layout = create_layout(LayoutType.VBOX, self._action_columns_widget)
        self._content_layout.addWidget(self._action_columns_widget)
        
        self._selected_value = self._add_info_row(tr_key='SLCTD', obj_name=(obj_name, 'Selected'))
        self._loaded_value = self._add_info_row(tr_key='LDD', obj_name=(obj_name, 'Loaded'))

        self._autoload_row = MTSwitchSetting(config=self._config, cfg_key=CKey.GENERAL_THEME, tr_key='ATLD_SLCTD_CFG', obj_name=(obj_name, 'Autoload'))
        self._actions_column_layout.addWidget(self._autoload_row)
        
        self._load_button = MTButton(tr_key='LD', obj_name=(obj_name, 'Apply'))
        self._actions_column_layout.addWidget(self._load_button)
        
        self._create_stack = self._build_inline_editor('Create', tr_key='CRT')
        self._actions_column_layout.addWidget(self._create_stack)
        
        self._rename_stack = self._build_inline_editor('Rename', tr_key='RNM')
        self._actions_column_layout.addWidget(self._rename_stack)

        self._delete_stack = self._build_delete_stack()
        self._actions_column_layout.addWidget(self._delete_stack)

        self._open_location_button = MTButton(tr_key='OPN_FL_LCTN', obj_name=(obj_name, 'Open_File_Location'))
        self._actions_column_layout.addWidget(self._open_location_button)

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
    ) -> MTInlineStackedWidget:
        obj_name = self.objectName()
        
        stack = MTInlineStackedWidget(obj_name=(obj_name, mode))
        
        button = MTButton(tr_key=tr_key, obj_name=(obj_name, mode))
        stack.addWidget(button)

        row = MTWidget(obj_name=(obj_name, mode, 'Editor_Row'))
        row_layout = create_layout(LayoutType.HBOX, row)
        stack.addWidget(row)
        
        line_edit = MTLineEdit(obj_name=(obj_name, mode, 'Editor'))
        row_layout.addWidget(line_edit, 1)
        
        cancel_button = MTButton(obj_name=(obj_name, mode, 'Editor_Cancel'))
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

    def _build_delete_stack(self) -> MTInlineStackedWidget:
        obj_name = self.objectName()
        
        stack = MTInlineStackedWidget(obj_name=(obj_name, 'Delete',))
        
        self._delete_button = MTButton(tr_key='DLT', obj_name=(obj_name, 'Delete'))
        stack.addWidget(self._delete_button)
        
        row = MTWidget(obj_name=(obj_name, 'Delete_Confirm_Row'))
        row_layout = create_layout(LayoutType.HBOX, row)
        stack.addWidget(row)
        
        self._delete_confirm = MTButton(tr_key='CNFRM', obj_name=(obj_name, 'Delete_Confirm'))
        row_layout.addWidget(self._delete_confirm, 1)
        
        self._delete_cancel = MTButton(obj_name=(obj_name, 'Delete_Cancel'))
        row_layout.addWidget(self._delete_cancel)
        
        return stack

    def _connect_signals(self) -> None:
        self._refresh_timer = QTimer(self, singleShot=True, interval=CONFIGS_REFRESH_DEBOUNCE_MS)
        self._refresh_timer.timeout.connect(self._refresh_themes)
        
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_THEMES_USER))
        self._watcher.directoryChanged.connect(self._on_themes_dir_changed)

        self._themes_list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._autoload_row.switch.toggled.connect(self._on_autoload_toggled)
        
        self._load_button.clicked.connect(self._load)
        self._open_location_button.clicked.connect(self._open_location)
        
        self._create_button.clicked.connect(self._start_create)
        self._create_line_edit.returnPressed.connect(self._submit_create)
        self._create_cancel_button.clicked.connect(self._cancel_create)
        
        self._rename_button.clicked.connect(self._start_rename)
        self._rename_line_edit.returnPressed.connect(self._submit_rename)
        self._rename_cancel_button.clicked.connect(self._cancel_rename)
        
        self._delete_button.clicked.connect(self._start_delete)
        self._delete_confirm.clicked.connect(self._submit_delete)
        self._delete_cancel.clicked.connect(self._cancel_delete)
        
        self._config.configLoaded.connect(self._on_config_loaded)

    def _on_config_loaded(self) -> None:
        self._refresh_themes()

    def _on_themes_dir_changed(self, _path: str) -> None:
        self._refresh_timer.start()
    
    def _on_selection_changed(self, new: MTListItem | None, _old: MTListItem | None) -> None:
        if new is None:
            return
        
        self._selected_name = new.text()
        self._sync_actions_state()

    def _on_autoload_toggled(self, checked: bool) -> None:
        selected = self._selected_name
        
        if checked:
            self._set_autoload_name(selected)
        elif self._autoload_name == selected:
            self._set_autoload_name(PATH_DEFAULT_THEME.stem)

        self._sync_actions_state()

    # load
    def _load(self, name: str | None) -> None:
        path = ctx.services.theme.load(name)
        if path is None:
            return
        
        self._loaded_name = path.stem
        self._config.set(CKey.GENERAL_THEME, path.stem)
        self._sync_actions_state()

    # create
    def _start_create(self) -> None:
        self._create_line_edit.clear()
        self._create_stack.setCurrentIndex(1)
        self._create_line_edit.setFocus()

    def _cancel_create(self) -> None:
        self._create_line_edit.clear()
        self._create_stack.setCurrentIndex(0)

    def _submit_create(self) -> None: # TODO
        name = FS.normalize_filename(self._create_line_edit.text())
        if name is None:
            return

        # self._config.create(name)
        self._cancel_create()
        self._refresh_themes()

    # rename
    def _start_rename(self) -> None:
        selected = self._selected_name
        if not selected:
            return
        
        self._rename_line_edit.setText(selected)
        self._rename_stack.setCurrentIndex(1)
        self._rename_line_edit.setFocus()
        self._rename_line_edit.selectAll()

    def _cancel_rename(self) -> None:
        self._rename_line_edit.clear()
        self._rename_stack.setCurrentIndex(0)

    def _submit_rename(self) -> None: # TODO
        selected = self._selected_name
        new_name = FS.normalize_filename(self._rename_line_edit.text())
        if new_name is None: # or not self._config.rename(selected, new_name):
            return

        if selected == self._autoload_name:
            self._set_autoload_name(new_name)

        self._cancel_rename()
        self._refresh_themes()

    # delete
    def _start_delete(self) -> None:
        self._delete_stack.setCurrentIndex(1)

    def _cancel_delete(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _submit_delete(self) -> None:
        selected = self._selected_name
        if self._autoload_name == selected:
            self._set_autoload_name(PATH_DEFAULT_THEME.stem)

        FS.delete_file(PATH_THEMES_USER / f'{selected}.txt')
        self._cancel_delete()
        self._refresh_themes()

    # open location
    def _open_location(self) -> None:
        path = PATH_THEMES_USER / f'{self._selected_name}.txt'
        if not path.is_file():
            self._refresh_themes()
            return

        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', str(path)])
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
    
    def _set_autoload_name(self, value: str) -> None:
        normalized = str(value).strip() or PATH_DEFAULT_THEME.stem
        if normalized == self._autoload_name:
            return
        
        self._config.set(CKey.GENERAL_THEME, normalized)
        self._autoload_name = normalized

    def _refresh_themes(self) -> None:
        names = FS.iter_paths(PATH_THEMES_USER, PATH_THEMES_SRC, file_extension='txt')
        
        if self._selected_name not in {name for name, _ in names}:
            # self._config.load()
            # self._selected_name = self._config.name
            ...
        
        with QSignalBlocker(self._themes_list_widget):
            self._themes_list_widget.setItems(names)

        self._sync_actions_state()

    def _sync_actions_state(self, *_args: object) -> None:
        autoload = self._autoload_name
        selected = self._selected_name

        self._selected_value.setText(selected)
        self._loaded_value.setText(ctx.services.theme.path.stem)

        has_selection = True
        self._autoload_row.switch.setEnabled(has_selection and not (selected == autoload == PATH_DEFAULT_THEME.stem))
        self._load_button.setEnabled(has_selection)
        self._rename_stack.setEnabled(has_selection)
        self._delete_stack.setEnabled(has_selection)
        self._open_location_button.setEnabled(has_selection)

        if not has_selection:
            self._cancel_rename()
            self._cancel_delete()

        with QSignalBlocker(self._autoload_row.switch):
            self._autoload_row.switch.setChecked(has_selection and selected == autoload)
