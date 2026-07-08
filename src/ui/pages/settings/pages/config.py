import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLayout, QSizePolicy, QStackedWidget

from src.app.paths import PATH_CONFIGS_USER
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.config.loader import ConfigLoader
from src.config.manager import Config
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTButton,
    MTInlineEditorStack,
    MTLabel,
    MTLabeledList,
    MTLineEdit,
    MTPlainLabel,
    MTSwitch,
    MTWidget,
    MTSwitchRowSetting,
)
from src.config.enums import ConfigLoaderKey as CLKey
from src.utils.filesystem import FS
from src.utils.filesystem.constants import FILENAME_SPECIAL_CHARS


class SettingsConfigPage(MTWidget):
    def __init__(self, *, config_loader: ConfigLoader, config: Config) -> None:
        super().__init__()
        self._config_loader = config_loader
        self._config = config
        FS.ensure_dir(PATH_CONFIGS_USER)
        self._autoload_name = self._read_autoload_name()

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        content = MTWidget(obj_name="Config_Page_Widget")
        main_layout.addWidget(content)

        body_layout = create_layout(LayoutType.HBOX, parent=content)

        self._list_column = MTLabeledList(
            obj_name="Config_List_Column",
            list_obj_name="Config_List",
        )
        self._configs_list = self._list_column.list_widget
        self._actions_column = MTWidget(obj_name="Config_Actions_Column")
        body_layout.addWidget(self._list_column, stretch=1)
        body_layout.addWidget(self._actions_column, stretch=1)

        self._build_actions_column()

        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_CONFIGS_USER))
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(CONFIGS_REFRESH_DEBOUNCE_MS)

        self._watcher.directoryChanged.connect(self._on_configs_dir_changed)
        self._refresh_timer.timeout.connect(self._refresh_configs)
        self._configs_list.currentItemChanged.connect(self._on_selection_changed)
        self._autoload_checkbox.toggled.connect(self._on_autoload_toggled)
        self._auto_save_checkbox.toggled.connect(self._on_auto_save_toggled)

        self._save_button.clicked.connect(self._save_selected_config)
        self._create_button.clicked.connect(self._start_create_edit)
        self._create_edit_line.returnPressed.connect(self._submit_create_edit)
        self._create_edit_cancel_button.clicked.connect(self._cancel_create_edit)
        self._rename_button.clicked.connect(self._start_rename_edit)
        self._rename_edit_line.returnPressed.connect(self._submit_rename_edit)
        self._rename_edit_cancel_button.clicked.connect(self._cancel_rename_edit)
        self._load_button.clicked.connect(self._load_selected_config)
        self._delete_button.clicked.connect(self._start_delete_confirm)
        self._delete_confirm_button.clicked.connect(self._delete_selected_config)
        self._delete_cancel_button.clicked.connect(self._cancel_delete_confirm)
        self._open_location_button.clicked.connect(self._open_selected_location)

        self._config.config_loaded.connect(self._on_config_loaded)

        self._refresh_configs(preferred=self._config.name)

    def _build_actions_column(self) -> None:
        layout = create_layout(LayoutType.VBOX, parent=self._actions_column)

        self._selected_value = self._add_info_row(
            layout=layout,
            tr_key="SLCTD",
            row_obj_name="Config_Selected_Info",
            label_obj_name="Config_Selected_Label",
            value_obj_name="Config_Selected_Value",
        )
        self._loaded_value = self._add_info_row(
            layout=layout,
            tr_key="LDD",
            row_obj_name="Config_Loaded_Info",
            label_obj_name="Config_Loaded_Label",
            value_obj_name="Config_Loaded_Value",
        )

        self._autoload_checkbox = MTSwitch(obj_name="Config_Autoload_Switch")
        autoload_row = MTSwitchRowSetting(
            tr_key="ATLD_SLCTD_CFG",
            switch=self._autoload_checkbox,
            obj_name="Config_Autoload",
        )
        layout.addWidget(autoload_row)

        self._auto_save_checkbox = MTSwitch(obj_name="Config_Auto_Save_Switch")
        auto_save_row = MTSwitchRowSetting(
            tr_key="AT_SV_CFG_CHNGS",
            switch=self._auto_save_checkbox,
            obj_name="Config_Auto_Save",
        )
        layout.addWidget(auto_save_row)

        self._save_button = MTButton(tr_key="SAVE", obj_name="Config_Save_Button")
        self._create_stack = self._build_inline_editor(
            mode="create",
            action_tr_key="CREATE",
            stack_obj_name="Config_Create_Stack",
            button_obj_name="Config_Create_Button",
            row_obj_name="Config_Create_Editor_Row",
            edit_obj_name="Config_Create_Editor_LineEdit",
            cancel_obj_name="Config_Create_Editor_Cancel_Button",
        )
        self._rename_stack = self._build_inline_editor(
            mode="rename",
            action_tr_key="RENAME",
            stack_obj_name="Config_Rename_Stack",
            button_obj_name="Config_Rename_Button",
            row_obj_name="Config_Rename_Editor_Row",
            edit_obj_name="Config_Rename_Editor_LineEdit",
            cancel_obj_name="Config_Rename_Editor_Cancel_Button",
        )
        self._load_button = MTButton(tr_key="LOAD", obj_name="Config_Load_Button")
        self._delete_stack = self._build_delete_confirm_stack(
            stack_obj_name="Config_Delete_Stack",
            button_obj_name="Config_Delete_Button",
            row_obj_name="Config_Delete_Confirm_Row",
            confirm_obj_name="Config_Delete_Confirm_Button",
            cancel_obj_name="Config_Delete_Cancel_Button",
        )
        self._open_location_button = MTButton(
            tr_key="OPN_FL_LCTN", obj_name="Config_Open_Location_Button"
        )
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
        action_tr_key: str,
        stack_obj_name: str,
        button_obj_name: str,
        row_obj_name: str,
        edit_obj_name: str,
        cancel_obj_name: str,
    ) -> QStackedWidget:
        stack = MTInlineEditorStack()
        stack.setObjectName(stack_obj_name)
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        button = MTButton(tr_key=action_tr_key, obj_name=button_obj_name)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stack.addWidget(button)

        editor_row = MTWidget(obj_name=row_obj_name)
        editor_row.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        editor_layout = create_layout(LayoutType.HBOX, parent=editor_row)
        line_edit = MTLineEdit(obj_name=edit_obj_name)
        line_edit.set_placeholder_tr_key("ENTER_CONFIG_NAME")
        line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        cancel_btn = MTButton(tr_key="✕", obj_name=cancel_obj_name)
        cancel_btn.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        editor_layout.addWidget(line_edit, 1)
        editor_layout.addWidget(cancel_btn)
        stack.addWidget(editor_row)

        match mode:
            case "create":
                self._create_button = button
                self._create_edit_line = line_edit
                self._create_edit_cancel_button = cancel_btn
            case "rename":
                self._rename_button = button
                self._rename_edit_line = line_edit
                self._rename_edit_cancel_button = cancel_btn
            case _:
                raise ValueError(f"Unsupported inline editor mode: {mode}")

        stack.setCurrentIndex(0)
        return stack

    def _build_delete_confirm_stack(
        self,
        *,
        stack_obj_name: str,
        button_obj_name: str,
        row_obj_name: str,
        confirm_obj_name: str,
        cancel_obj_name: str,
    ) -> QStackedWidget:
        stack = MTInlineEditorStack()
        stack.setObjectName(stack_obj_name)
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._delete_button = MTButton(tr_key="DELETE", obj_name=button_obj_name)
        self._delete_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        stack.addWidget(self._delete_button)

        confirm_row = MTWidget(obj_name=row_obj_name)
        confirm_row.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        confirm_layout = create_layout(LayoutType.HBOX, parent=confirm_row)
        self._delete_confirm_button = MTButton(
            tr_key="Confirm", obj_name=confirm_obj_name
        )
        self._delete_cancel_button = MTButton(tr_key="✕", obj_name=cancel_obj_name)
        self._delete_confirm_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._delete_cancel_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        confirm_layout.addWidget(self._delete_confirm_button, 1)
        confirm_layout.addWidget(self._delete_cancel_button)
        stack.addWidget(confirm_row)
        stack.setCurrentIndex(0)
        return stack

    def _add_info_row(
        self,
        *,
        layout: QLayout,
        tr_key: str,
        row_obj_name: str,
        label_obj_name: str,
        value_obj_name: str,
    ) -> MTPlainLabel:
        row = MTWidget(obj_name=row_obj_name)
        row_layout = create_layout(LayoutType.HBOX, parent=row)
        label = MTLabel(tr_key=tr_key, obj_name=label_obj_name)
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(label)
        value_label = MTPlainLabel("-", obj_name=value_obj_name)
        value_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        row_layout.addWidget(value_label, stretch=1)
        layout.addWidget(row)
        return value_label

    def _iter_config_names(self) -> list[str]:
        names: list[str] = []
        for file_path in PATH_CONFIGS_USER.glob("*.txt"):
            if not file_path.is_file():
                continue
            stem = file_path.stem
            if not stem or stem.startswith("."):
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
        return PATH_CONFIGS_USER / f"{selected}.txt"

    def _read_autoload_name(self) -> str:
        return str(self._config_loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default=CONFIG_DEFAULT_NAME)).strip() or CONFIG_DEFAULT_NAME

    def _set_autoload_name(self, value: str) -> str:
        normalized = str(value).strip() or CONFIG_DEFAULT_NAME
        if normalized == self._autoload_name:
            return self._autoload_name
        self._config_loader.set(CLKey.LOADER_CONFIG_ON_LOAD, normalized)
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
        return selected == CONFIG_DEFAULT_NAME and autoload == CONFIG_DEFAULT_NAME

    def _refresh_configs(self, *, preferred: str | None = None) -> None:
        names = self._iter_config_names()
        target = self._pick_target_name(names, preferred=preferred)
        with QSignalBlocker(self._configs_list):
            items_rebuilt = self._list_column.set_items(names, preferred=target)

        self._sync_actions_state()
        if items_rebuilt:
            self._reapply_window_theme()

    def _reapply_window_theme(self) -> None:
        window = self.window()
        if window is self:
            return
        window = cast(Any, window)
        window.reapply_loaded_theme()

    def _sync_actions_state(self) -> None:
        selected = self._current_selected_name()
        autoload = self._autoload_name
        loaded = self._config.name

        self._selected_value.setText(selected or "-")
        self._loaded_value.setText(loaded or "-")

        has_selection = selected is not None
        is_default_autoload_locked = self._is_default_autoload_locked(
            selected, autoload
        )
        self._load_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)
        self._delete_stack.setEnabled(has_selection)
        self._rename_button.setEnabled(has_selection)
        self._rename_stack.setEnabled(has_selection)
        self._open_location_button.setEnabled(has_selection)
        self._autoload_checkbox.setEnabled(
            has_selection and not is_default_autoload_locked
        )
        self._save_button.setEnabled(has_selection)
        self._create_stack.setEnabled(True)

        if not has_selection and self._rename_stack.currentIndex() == 1:
            self._cancel_rename_edit()
        if not has_selection and self._delete_stack.currentIndex() == 1:
            self._cancel_delete_confirm()

        with QSignalBlocker(self._autoload_checkbox):
            self._autoload_checkbox.setChecked(has_selection and selected == autoload)
        with QSignalBlocker(self._auto_save_checkbox):
            self._auto_save_checkbox.setChecked(bool(self._config_loader.auto_save_config))

    def _on_selection_changed(self, *_args: object) -> None:
        self._sync_actions_state()

    def _on_configs_dir_changed(self, _path: str) -> None:
        self._refresh_timer.start()

    def _on_autoload_toggled(self, checked: bool) -> None:
        selected = self._current_selected_name()
        if not selected:
            return

        if not checked and self._is_default_autoload_locked(
            selected, self._autoload_name
        ):
            with QSignalBlocker(self._autoload_checkbox):
                self._autoload_checkbox.setChecked(True)
            self._sync_actions_state()
            return

        if checked:
            self._set_autoload_name(selected)
        elif self._autoload_name == selected:
            self._set_autoload_name(CONFIG_DEFAULT_NAME)

        self._sync_actions_state()

    def _on_auto_save_toggled(self, checked: bool) -> None:
        self._config_loader.set(CLKey.SAVER_AUTO_SAVE_CONFIG_CHANGES, bool(checked))
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
        name = str(value).strip().removesuffix(".txt")
        if (
            not name
            or name.startswith(".")
            or any(char in name for char in FILENAME_SPECIAL_CHARS)
        ):
            return ""
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
            self._set_autoload_name(CONFIG_DEFAULT_NAME)

        self._cancel_delete_confirm()
        self._refresh_configs(preferred=self._config.name)

    def _open_selected_location(self) -> None:
        config_path = self._selected_config_path()
        if config_path is None:
            return
        if not config_path.exists():
            self._refresh_configs()
            return

        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(config_path)])
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(config_path).parent)))

    def _on_config_loaded(self) -> None:
        self._refresh_configs(preferred=self._config.name)
