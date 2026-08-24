from __future__ import annotations

import typing as t

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer
from PySide6.QtWidgets import QWidget, QStackedWidget

from src.app.paths import PATH_DEFAULT_CONFIG, PATH_CONFIGS_SRC, PATH_CONFIGS_USER
from src.translation import Translation as Tr
from src.ui.pages.base import BasePage
from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTButton, MTInlineStackedWidget, MTLabel, MTLineEdit, MTList, MTPlainLabel, MTWidget
from src.ui.widgets.settings import MTSwitchSetting
from src.config import ConfigLoaderKey as CLKey
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.utils.filesystem import FS
from src.utils.desktop import Desktop

if t.TYPE_CHECKING:
    from src.config import Config
    from src.ui.widgets.common import MTListItem


class SettingsConfigPage(BasePage):
    _OBJECT_NAME = 'Config'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, config=config, obj_name=(*obj_name, SettingsConfigPage._OBJECT_NAME))

        self._auto_save = self._config.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, bool)
        self._autoload_name = self._config.loader.get(CLKey.LOADER_CONFIG_ON_LOAD, str)
        
        self._build_ui()
        self._connect_signals()
        
        self._refresh_configs()

    def _build_ui(self) -> None:
        obj_name = self.objectName()
        
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._main_content_widget = MTWidget(obj_name=(obj_name, 'Content'))
        self._main_content_layout = create_layout(LayoutType.HBOX, self._main_content_widget)
        self._main_layout.addWidget(self._main_content_widget)
        
        self._configs_list_widget = MTList(obj_name=(obj_name, 'List_Column'))
        self._main_content_layout.addWidget(self._configs_list_widget)
        
        self._actions_column_widget = MTWidget(obj_name=(obj_name, 'Actions_Column'))
        self._actions_column_layout = create_layout(LayoutType.VBOX, self._actions_column_widget)
        self._main_content_layout.addWidget(self._actions_column_widget)
        
        self._selected_value = self._add_info_row(tr=Tr(key='SLCTD'), obj_name=(obj_name, 'Selected'))
        self._loaded_value = self._add_info_row(tr=Tr(key='LDD'), obj_name=(obj_name, 'Loaded'))

        self._autoload_row = MTSwitchSetting(config=self._config.loader, cfg_key=CLKey.LOADER_CONFIG_ON_LOAD, tr=Tr(key='ATLD_SLCTD_CFG'), obj_name=(obj_name, 'Autoload'))
        self._actions_column_layout.addWidget(self._autoload_row)
        
        self._auto_save_row = MTSwitchSetting(config=self._config.loader, cfg_key=CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, tr=Tr(key='AT_SV_CFG_CHNGS'), obj_name=(obj_name, 'Auto_Save'))
        self._actions_column_layout.addWidget(self._auto_save_row)

        self._load_button = MTButton(tr=Tr(key='LD'), obj_name=(obj_name, 'Load'))
        self._actions_column_layout.addWidget(self._load_button)
        
        self._save_button = MTButton(tr=Tr(key='SV'), obj_name=(obj_name, 'Save'))
        self._actions_column_layout.addWidget(self._save_button)

        self._create_stack = self._build_inline_editor('Create', tr=Tr(key='CRT'))
        self._actions_column_layout.addWidget(self._create_stack)
        
        self._rename_stack = self._build_inline_editor('Rename', tr=Tr(key='RNM'))
        self._actions_column_layout.addWidget(self._rename_stack)

        self._delete_stack = self._build_delete_stack()
        self._actions_column_layout.addWidget(self._delete_stack)

        self._open_location_button = MTButton(tr=Tr(key='OPN_FL_LCTN'), obj_name=(obj_name, 'Open_File_Location'))
        self._actions_column_layout.addWidget(self._open_location_button)
        
        self._actions_column_layout.addStretch()

    def _add_info_row(
        self,
        *,
        tr: Tr = Tr(),
        obj_name: tuple[str, ...] = (),
    ) -> MTPlainLabel:        
        row = MTWidget(obj_name=(*obj_name, 'Row'))
        row_layout = create_layout(LayoutType.HBOX, row)
        
        label = MTLabel(tr=tr, obj_name=obj_name)
        row_layout.addWidget(label)
        
        value_label = MTPlainLabel(text='-', obj_name=(*obj_name, 'Value'))
        row_layout.addWidget(value_label, stretch=1)
        
        self._actions_column_layout.addWidget(row)
        
        return value_label

    def _build_inline_editor(
        self,
        mode: str,
        *,
        tr: Tr = Tr(),
    ) -> MTInlineStackedWidget:
        obj_name = self.objectName()
        
        stack = MTInlineStackedWidget(obj_name=(obj_name, mode))
        
        button = MTButton(tr=tr, obj_name=(obj_name, mode))
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

    def _build_delete_stack(self) -> QStackedWidget:
        obj_name = self.objectName()
        
        stack = MTInlineStackedWidget(obj_name=(obj_name, 'Delete'))

        self._delete_button = MTButton(tr=Tr(key='DLT'), obj_name=(obj_name, 'Delete'))
        stack.addWidget(self._delete_button)

        confirm_row = MTWidget(obj_name=(obj_name, 'Delete_Confirm_Row'))
        confirm_layout = create_layout(LayoutType.HBOX, confirm_row)
        stack.addWidget(confirm_row)
        
        self._delete_confirm_button = MTButton(tr=Tr(key='CNFRM'), obj_name=(obj_name, 'Delete_Confirm'))
        confirm_layout.addWidget(self._delete_confirm_button, 1)
        
        self._delete_cancel_button = MTButton(obj_name=(obj_name, 'Delete_Cancel'))
        confirm_layout.addWidget(self._delete_cancel_button)
        
        stack.setCurrentIndex(0)
        return stack

    def _connect_signals(self) -> None:
        self._refresh_timer = QTimer(self, singleShot=True, interval=CONFIGS_REFRESH_DEBOUNCE_MS)
        self._refresh_timer.timeout.connect(self._refresh_configs)
        
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_CONFIGS_USER))
        self._watcher.directoryChanged.connect(self._on_configs_dir_changed)

        self._configs_list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._autoload_row.switch.toggled.connect(self._on_autoload_toggled)
        self._auto_save_row.switch.toggled.connect(self._on_auto_save_toggled)

        self._load_button.clicked.connect(self._load)
        self._save_button.clicked.connect(self._save)
        self._open_location_button.clicked.connect(self._open_location)
        
        self._create_button.clicked.connect(self._start_create)
        self._create_cancel_button.clicked.connect(self._cancel_create)
        self._create_line_edit.returnPressed.connect(self._submit_create)
        
        self._rename_button.clicked.connect(self._start_rename)
        self._rename_cancel_button.clicked.connect(self._cancel_rename)
        self._rename_line_edit.returnPressed.connect(self._submit_rename)
        
        self._delete_button.clicked.connect(self._start_delete)
        self._delete_cancel_button.clicked.connect(self._cancel_delete)
        self._delete_confirm_button.clicked.connect(self._submit_delete)

    def _on_configs_dir_changed(self, _path: str) -> None:
        self._refresh_timer.start()

    def _on_selection_changed(self, _new: MTListItem | None, _old: MTListItem | None) -> None:
        self._sync_actions_state()

    def _on_autoload_toggled(self, checked: bool) -> None:
        selected_text = self._configs_list_widget.currentText
        if selected_text is None:
            return
        
        if checked:
            self._set_autoload_name(selected_text)
        elif selected_text == self._autoload_name:
            self._set_autoload_name(PATH_DEFAULT_CONFIG.stem)

        self._sync_actions_state()

    def _on_auto_save_toggled(self, checked: bool) -> None:
        self._auto_save = checked
        self._config.loader.set(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, checked)

    # load
    def _load(self) -> None:
        self._config.load(self._configs_list_widget.currentText)
        self._sync_actions_state()
    
    # save
    def _save(self) -> None:
        selected_path = self._configs_list_widget.currentValue
        if selected_path is None:
            return
        
        if selected_path != self._config.path:
            self._config.create(selected_path.stem, overwrite=True)
        else:
            self._config.save()
    
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

        self._config.create(name)
        self._cancel_create()
        self._refresh_configs()

    # rename
    def _start_rename(self) -> None:
        selected_text = self._configs_list_widget.currentText
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
        selected_text = self._configs_list_widget.currentText      
        new_name = FS.normalize_filename(self._rename_line_edit.text())
        if (
            selected_text is None
            or not new_name
            or not self._config.rename(selected_text, new_name)
        ):
            return

        if selected_text == self._autoload_name:
            self._set_autoload_name(new_name)

        self._cancel_rename()
        self._refresh_configs()

    # delete
    def _start_delete(self) -> None:
        self._delete_stack.setCurrentIndex(1)
    
    def _cancel_delete(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _submit_delete(self) -> None:
        selected_text = self._configs_list_widget.currentText
        if selected_text == self._autoload_name:
            self._set_autoload_name(PATH_DEFAULT_CONFIG.stem)

        FS.delete_file(PATH_CONFIGS_USER / f'{selected_text}.txt')
        self._cancel_delete()
        self._refresh_configs()

    # open location
    def _open_location(self) -> None:
        selected_path = self._configs_list_widget.currentValue
        if selected_path is None:
            return
        
        if not selected_path.is_file():
            self._refresh_configs()
            return

        Desktop.open_file_location(selected_path)

    def _set_autoload_name(self, value: str) -> None:
        name = value.strip() or PATH_DEFAULT_CONFIG.stem
        if name == self._autoload_name:
            return
        
        self._config.loader.set(CLKey.LOADER_CONFIG_ON_LOAD, name)
        self._autoload_name = name

    def _refresh_configs(self) -> None:
        paths = FS.iter_paths(PATH_CONFIGS_USER, PATH_CONFIGS_SRC, file_extension='txt', remove_duplicate_filenames=True)
        items = tuple((path, path.stem) for path in paths)
        
        with QSignalBlocker(self._configs_list_widget):
            self._configs_list_widget.setItems(items)

        self._sync_actions_state()

    def _sync_actions_state(self) -> None:
        item = self._configs_list_widget.currentItem
        path = item.value if item else None
        stem = path.stem if path else None

        self._selected_value.setText(stem or '-')
        self._loaded_value.setText(self._config.path.stem)

        is_selected = path is not None
        is_user_path = FS.is_user_path(path)
        can_modify = is_selected and is_user_path

        with QSignalBlocker(self._autoload_row.switch):
            self._autoload_row.switch.setChecked(can_modify and stem == self._autoload_name)
        with QSignalBlocker(self._auto_save_row.switch):
            self._auto_save_row.switch.setChecked(can_modify and self._config.loader.get(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, bool))
        
        self._autoload_row.switch.setEnabled(not (stem == self._autoload_name == PATH_DEFAULT_CONFIG.stem))
        self._auto_save_row.switch.setEnabled(can_modify and self._auto_save)
        self._load_button.setEnabled(is_selected)
        self._save_button.setEnabled(can_modify)
        self._rename_stack.setEnabled(can_modify)
        self._delete_stack.setEnabled(can_modify)
        self._open_location_button.setEnabled(can_modify)

        if not is_selected:
            self._cancel_rename()
            self._cancel_delete()
