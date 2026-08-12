from __future__ import annotations

import typing as t

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer
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
    
    def _on_selection_changed(self, _new: MTListItem | None, _old: MTListItem | None) -> None:
        self._sync_actions_state()

    def _on_autoload_toggled(self, checked: bool) -> None:
        selected_text = self._themes_list_widget.currentText
        if selected_text is None:
            return
        
        if checked:
            self._set_autoload_name(selected_text)
        elif selected_text == self._autoload_name:
            self._set_autoload_name(PATH_DEFAULT_THEME.stem)

        self._sync_actions_state()

    # load
    def _load(self) -> None:
        ctx.services.theme.load(self._themes_list_widget.currentText)

    # create
    def _start_create(self) -> None:
        self._create_line_edit.clear()
        self._create_stack.setCurrentIndex(1)
        self._create_line_edit.setFocus()

    def _cancel_create(self) -> None:
        self._create_stack.setCurrentIndex(0)
        self._create_line_edit.clear()

    def _submit_create(self) -> None:
        name = FS.normalize_filename(self._create_line_edit.text())
        if name is None:
            return

        self._cancel_create()
        # self._config.create(name) > ctx.services.theme.create(name)
        self._refresh_themes()

    # rename
    def _start_rename(self) -> None:
        selected_text = self._themes_list_widget.currentText
        if not selected_text:
            return
        
        self._rename_line_edit.setText(selected_text)
        self._rename_stack.setCurrentIndex(1)
        self._rename_line_edit.setFocus()
        self._rename_line_edit.selectAll()

    def _cancel_rename(self) -> None:
        self._rename_stack.setCurrentIndex(0)
        self._rename_line_edit.clear()

    def _submit_rename(self) -> None:
        selected_text = self._themes_list_widget.currentText      
        new_name = FS.normalize_filename(self._rename_line_edit.text())
        if (
            selected_text is None
            or not new_name
            # or not self._config.rename(selected_text, new_name) > ctx.services.theme.rename(selected_text, new_name)
        ):
            return

        if selected_text == self._autoload_name:
            self._set_autoload_name(new_name)

        self._cancel_rename()
        self._refresh_themes()

    # delete
    def _start_delete(self) -> None:
        self._delete_stack.setCurrentIndex(1)

    def _cancel_delete(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _submit_delete(self) -> None:
        selected_text = self._themes_list_widget.currentText
        if selected_text == self._autoload_name:
            self._set_autoload_name(PATH_DEFAULT_THEME.stem)

        FS.delete_file(PATH_THEMES_USER / f'{selected_text}.txt')
        self._cancel_delete()
        self._refresh_themes()

    # open location
    def _open_location(self) -> None:
        selected_path = self._themes_list_widget.currentValue
        if selected_path is None:
            return
        
        if not selected_path.is_file():
            self._refresh_themes()
            return

        FS.open_file_location(selected_path)
    
    def _set_autoload_name(self, value: str) -> None:
        name = value.strip() or PATH_DEFAULT_THEME.stem
        if name == self._autoload_name:
            return
        
        self._config.set(CKey.GENERAL_THEME, name)
        self._autoload_name = name

    def _refresh_themes(self) -> None:
        paths = FS.iter_paths(PATH_THEMES_USER, PATH_THEMES_SRC, file_extension='txt', remove_duplicate_filenames=True)
        items = tuple((path, path.stem) for path in paths)

        with QSignalBlocker(self._themes_list_widget):
            self._themes_list_widget.setItems(items)

        self._sync_actions_state()

    def _sync_actions_state(self) -> None:
        item = self._themes_list_widget.currentItem
        path = item.value if item else None
        stem = path.stem if path else None

        self._selected_value.setText(stem or '-')
        self._loaded_value.setText(ctx.services.theme.path.stem)

        is_selected = path is not None
        is_user_path = FS.is_user_path(path)
        can_modify = is_selected and is_user_path

        with QSignalBlocker(self._autoload_row.switch):
            self._autoload_row.switch.setChecked(can_modify and stem == self._autoload_name)

        self._autoload_row.switch.setEnabled(not (stem == self._autoload_name == PATH_DEFAULT_THEME.stem))
        self._load_button.setEnabled(is_selected)
        self._rename_stack.setEnabled(can_modify)
        self._delete_stack.setEnabled(can_modify)
        self._open_location_button.setEnabled(can_modify)

        if not is_selected:
            self._cancel_rename()
            self._cancel_delete()
