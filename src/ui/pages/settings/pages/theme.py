import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLayout, QSizePolicy, QStackedWidget

from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.config.loader import config_loader
from src.config.manager import config
from src.theme.paths import PATH_DEFAULT_THEME, PATH_THEMES_SOURCE, PATH_THEMES_USER
from src.theme.storage.io import (
    find_theme_file_by_name,
    iter_theme_files,
    load_theme_payload,
    normalize_theme_name,
    theme_output_path,
    write_theme_payload,
)
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
from src.utils.filesystem import FS
from src.utils.filesystem.constants import FILENAME_SPECIAL_CHARS
from src.config.enums import ConfigLoaderKey as CLKey


class SettingsThemePage(MTWidget):
    def __init__(self, *, autoload_name: str | None = None):
        super().__init__()
        FS.ensure_dir(PATH_THEMES_USER)

        self._themes_by_name: dict[str, Path] = {}
        self._autoload_name = (
            self._normalize_theme_name(autoload_name)
            if autoload_name is not None
            else self._read_autoload_name()
        )
        self._autoload_enabled = self._read_autoload_enabled()
        self._applied_name = self._autoload_name

        main_layout = create_layout(LayoutType.VBOX, parent=self)
        content = MTWidget(obj_name="Theme_Page_Widget")
        main_layout.addWidget(content)

        body_layout = create_layout(LayoutType.HBOX, parent=content)
        self._list_column = MTLabeledList(
            obj_name="Theme_List_Column",
            list_obj_name="Theme_List",
        )
        self._themes_list = self._list_column.list_widget
        self._actions_column = MTWidget(obj_name="Theme_Actions_Column")
        body_layout.addWidget(self._list_column, stretch=1)
        body_layout.addWidget(self._actions_column, stretch=1)

        self._build_actions_column()

        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_THEMES_USER))
        # if PATH_THEMES_SOURCE.exists():
        #     self._watcher.addPath(str(PATH_THEMES_SOURCE))

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(CONFIGS_REFRESH_DEBOUNCE_MS)

        self._watcher.directoryChanged.connect(self._on_themes_dir_changed)
        self._refresh_timer.timeout.connect(self._refresh_themes)
        self._themes_list.currentItemChanged.connect(self._on_selection_changed)
        self._autoload_switch.toggled.connect(self._on_autoload_toggled)
        self._auto_save_switch.toggled.connect(self._on_auto_save_toggled)
        self._load_button.clicked.connect(self._load_selected_theme)
        self._save_button.clicked.connect(self._save_selected_theme)
        self._create_button.clicked.connect(self._start_create_edit)
        self._create_edit_line.returnPressed.connect(self._submit_create_edit)
        self._create_edit_cancel_button.clicked.connect(self._cancel_create_edit)
        self._rename_button.clicked.connect(self._start_rename_edit)
        self._rename_edit_line.returnPressed.connect(self._submit_rename_edit)
        self._rename_edit_cancel_button.clicked.connect(self._cancel_rename_edit)
        self._delete_button.clicked.connect(self._start_delete_confirm)
        self._delete_confirm_button.clicked.connect(self._delete_selected_theme)
        self._delete_cancel_button.clicked.connect(self._cancel_delete_confirm)
        self._open_location_button.clicked.connect(self._open_selected_location)

        config.config_loaded.connect(self._on_config_loaded)

        self._refresh_themes(preferred=self._autoload_name)

    def _build_actions_column(self) -> None:
        layout = create_layout(LayoutType.VBOX, parent=self._actions_column)

        self._selected_value = self._add_info_row(
            layout=layout,
            tr_key="SLCTD",
            row_obj_name="Theme_Selected_Info",
            label_obj_name="Theme_Selected_Label",
            value_obj_name="Theme_Selected_Value",
        )
        self._loaded_value = self._add_info_row(
            layout=layout,
            tr_key="LDD",
            row_obj_name="Theme_Loaded_Info",
            label_obj_name="Theme_Loaded_Label",
            value_obj_name="Theme_Loaded_Value",
        )

        self._autoload_switch = MTSwitch(obj_name="Theme_Autoload_Switch")
        autoload_row = MTSwitchRowSetting(
            tr_key="ATLD_SLCTD_THM",
            switch=self._autoload_switch,
            obj_name="Theme_Autoload",
        )
        layout.addWidget(autoload_row)

        self._auto_save_switch = MTSwitch(obj_name="Theme_Auto_Save_Switch")
        auto_save_row = MTSwitchRowSetting(
            tr_key="AT_SV_THM_CHNGS",
            switch=self._auto_save_switch,
            obj_name="Theme_Auto_Save",
        )
        layout.addWidget(auto_save_row)

        self._load_button = MTButton(tr_key="LOAD", obj_name="Theme_Apply_Button")
        self._save_button = MTButton(tr_key="SAVE", obj_name="Theme_Save_Button")
        self._create_stack = self._build_inline_editor(
            mode="create",
            action_tr_key="CREATE",
            stack_obj_name="Theme_Create_Stack",
            button_obj_name="Theme_Create_Button",
            row_obj_name="Theme_Create_Editor_Row",
            edit_obj_name="Theme_Create_Editor_LineEdit",
            cancel_obj_name="Theme_Create_Editor_Cancel_Button",
        )
        self._rename_stack = self._build_inline_editor(
            mode="rename",
            action_tr_key="RENAME",
            stack_obj_name="Theme_Rename_Stack",
            button_obj_name="Theme_Rename_Button",
            row_obj_name="Theme_Rename_Editor_Row",
            edit_obj_name="Theme_Rename_Editor_LineEdit",
            cancel_obj_name="Theme_Rename_Editor_Cancel_Button",
        )
        self._delete_stack = self._build_delete_confirm_stack(
            stack_obj_name="Theme_Delete_Stack",
            button_obj_name="Theme_Delete_Button",
            row_obj_name="Theme_Delete_Confirm_Row",
            confirm_obj_name="Theme_Delete_Confirm_Button",
            cancel_obj_name="Theme_Delete_Cancel_Button",
        )
        self._open_location_button = MTButton(
            tr_key="OPN_FL_LCTN", obj_name="Theme_Open_Location_Button"
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
        line_edit.set_placeholder_tr_key("ENTER_THEME_NAME")
        line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        cancel_btn = MTButton(tr_key="✕", obj_name=cancel_obj_name)
        cancel_btn.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        cancel_btn.setProperty("rainbowBorderTarget", False)
        cancel_btn.setProperty("rainbowBorderExcluded", True)
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
            tr_key="CONFIRM", obj_name=confirm_obj_name
        )
        self._delete_cancel_button = MTButton(tr_key="✕", obj_name=cancel_obj_name)
        self._delete_confirm_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._delete_cancel_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        self._delete_cancel_button.setProperty("rainbowBorderTarget", False)
        self._delete_cancel_button.setProperty("rainbowBorderExcluded", True)
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
        row.setProperty("rainbowBorderTarget", True)
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

    def _build_theme_map(self) -> dict[str, Path]:
        theme_map: dict[str, Path] = {}

        if PATH_THEMES_SOURCE.exists():
            for path in iter_theme_files(PATH_THEMES_SOURCE):
                theme_map[path.stem] = path

        for path in iter_theme_files(PATH_THEMES_USER):
            theme_map[path.stem] = path

        return theme_map

    def _iter_theme_names(self) -> list[str]:
        names = [name for name in self._themes_by_name.keys() if name]
        names.sort(key=str.casefold)
        return names

    def _current_selected_name(self) -> str | None:
        return self._list_column.current_value()

    def _selected_theme_path(self) -> Path | None:
        if not (selected := self._current_selected_name()):
            return None
        return self._themes_by_name.get(selected)

    def _read_autoload_name(self) -> str:
        return self._normalize_theme_name(
            config.get("General>Theme", default=PATH_DEFAULT_THEME.stem)
        )

    def _read_autoload_enabled(self) -> bool:
        return bool(config.get("Theme>Autoload Selected Theme", default=True))

    def _normalize_theme_name(self, value: Any) -> str:
        normalized = normalize_theme_name(str(value or ""))
        return normalized or PATH_DEFAULT_THEME.stem

    def _set_autoload_name(self, value: str, *, force_save: bool = False) -> str:
        normalized = normalize_theme_name(value) or PATH_DEFAULT_THEME.stem
        if normalized == self._autoload_name:
            return self._autoload_name
        config.set("General>Theme", normalized, force_save=force_save)
        self._autoload_name = normalized
        return normalized

    def _set_autoload_enabled(self, enabled: bool, *, force_save: bool = True) -> bool:
        enabled = bool(enabled)
        if enabled == self._autoload_enabled:
            return self._autoload_enabled
        config.set("Theme>Autoload Selected Theme", enabled, force_save=force_save)
        self._autoload_enabled = enabled
        return enabled

    def _read_applied_name(self) -> str:
        window = cast(Any, self.window())
        current = str(window.current_theme_name()).strip()
        return self._normalize_theme_name(current or self._applied_name)

    def _pick_target_name(
        self, names: list[str], preferred: str | None = None
    ) -> str | None:
        for candidate in (
            preferred,
            self._current_selected_name(),
            self._applied_name,
            PATH_DEFAULT_THEME.stem,
        ):
            if candidate in names:
                return candidate
        return names[0] if names else None

    def _is_user_theme(self, theme_path: Path | None) -> bool:
        if theme_path is None:
            return False
        try:
            theme_path.resolve().relative_to(PATH_THEMES_USER.resolve())
            return True
        except ValueError:
            return False

    def _refresh_themes(self, *, preferred: str | None = None) -> None:
        self._themes_by_name = self._build_theme_map()
        names = self._iter_theme_names()
        target = self._pick_target_name(names, preferred=preferred)

        with QSignalBlocker(self._themes_list):
            items_rebuilt = self._list_column.set_items(names, preferred=target)

        self._sync_actions_state()
        if items_rebuilt:
            self._reapply_window_theme()

    def _reapply_window_theme(self) -> None:
        window = cast(Any, self.window())
        theme_manager = window._theme_manager
        if theme_manager is None:
            return

        theme_manager.apply()
        window._reload_main_animations_from_theme()
        window.reapply_runtime_theme_preferences()

    def _sync_actions_state(self) -> None:
        selected = self._current_selected_name()
        theme_path = self._selected_theme_path()
        autoload = self._autoload_name
        autoload_enabled = self._autoload_enabled
        applied = self._read_applied_name()
        self._applied_name = applied
        has_selection = selected is not None
        is_user_theme = self._is_user_theme(theme_path)

        self._selected_value.setText(selected or "-")
        self._loaded_value.setText(applied or "-")

        self._load_button.setEnabled(has_selection)
        self._save_button.setEnabled(has_selection)
        self._rename_stack.setEnabled(has_selection and is_user_theme)
        self._rename_button.setEnabled(has_selection and is_user_theme)
        self._delete_button.setEnabled(has_selection and is_user_theme)
        self._delete_stack.setEnabled(has_selection and is_user_theme)
        self._open_location_button.setEnabled(has_selection)
        self._autoload_switch.setEnabled(has_selection)
        self._create_stack.setEnabled(True)

        if (
            not has_selection or not is_user_theme
        ) and self._rename_stack.currentIndex() == 1:
            self._cancel_rename_edit()
        if (
            not has_selection or not is_user_theme
        ) and self._delete_stack.currentIndex() == 1:
            self._cancel_delete_confirm()

        with QSignalBlocker(self._autoload_switch):
            self._autoload_switch.setChecked(
                has_selection and autoload_enabled and selected == autoload
            )
        with QSignalBlocker(self._auto_save_switch):
            self._auto_save_switch.setChecked(bool(config_loader.auto_save_theme))

    def _on_themes_dir_changed(self, _path: str) -> None:
        self._refresh_timer.start()

    def _on_selection_changed(self, *_args: object) -> None:
        self._sync_actions_state()

    def _on_autoload_toggled(self, checked: bool) -> None:
        if not (selected := self._current_selected_name()):
            return

        if checked:
            self._set_autoload_name(selected, force_save=True)
            self._set_autoload_enabled(True)
        else:
            self._set_autoload_enabled(False)

        self._sync_actions_state()

    def _on_auto_save_toggled(self, checked: bool) -> None:
        config_loader.set(CLKey.SAVER_AUTO_SAVE_THEME_CHANGES, bool(checked))
        self._sync_actions_state()

    def _load_selected_theme(self) -> None:
        if not (selected := self._current_selected_name()):
            return

        window = cast(Any, self.window())
        window.set_theme(selected, persist=False)
        self._applied_name = self._read_applied_name()

        self._autoload_name = self._read_autoload_name()
        self._sync_actions_state()

    def _save_selected_theme(self) -> None:
        if not (selected := self._current_selected_name()):
            return

        window = cast(Any, self.window())
        if window.save_current_theme_as(selected) is None:
            return
        self._refresh_themes(preferred=selected)

    def _normalize_new_name(self, value: str) -> str:
        name = normalize_theme_name(value)
        if (
            not name
            or name.startswith(".")
            or any(char in name for char in FILENAME_SPECIAL_CHARS)
        ):
            return ""
        return name

    def _theme_template_payload(self) -> dict[str, Any]:
        if (selected_path := self._selected_theme_path()) is not None:
            return load_theme_payload(selected_path)
        return {"widgets": []}

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

        output_path = find_theme_file_by_name(
            PATH_THEMES_USER, name
        ) or theme_output_path(PATH_THEMES_USER, name)
        if output_path.exists():
            return

        payload = self._theme_template_payload()

        try:
            write_theme_payload(output_path, payload)
        except OSError:
            return

        self._cancel_create_edit()
        self._refresh_themes(preferred=name)

    def _start_rename_edit(self) -> None:
        if not (selected := self._current_selected_name()):
            return
        if not self._is_user_theme(self._selected_theme_path()):
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
        if not self._is_user_theme(self._selected_theme_path()):
            return
        self._delete_stack.setCurrentIndex(1)

    def _cancel_delete_confirm(self) -> None:
        self._delete_stack.setCurrentIndex(0)

    def _submit_rename_edit(self) -> None:
        old_name = self._current_selected_name()
        old_path = self._selected_theme_path()
        if old_name is None or old_path is None or not self._is_user_theme(old_path):
            self._cancel_rename_edit()
            return

        new_name = self._normalize_new_name(self._rename_edit_line.text())
        if not new_name:
            return
        if new_name == old_name:
            self._cancel_rename_edit()
            return

        existing_user_theme = find_theme_file_by_name(PATH_THEMES_USER, new_name)
        new_path = existing_user_theme or theme_output_path(
            PATH_THEMES_USER, new_name, preferred_suffix=old_path.suffix
        )
        if new_path.exists():
            return

        try:
            old_path.rename(new_path)
        except OSError:
            return

        if self._autoload_name == old_name:
            self._set_autoload_name(new_name)

        applied = self._applied_name
        if applied == old_name:
            cast(Any, self.window()).set_theme(new_name, persist=False)
            self._applied_name = self._read_applied_name()

        self._cancel_rename_edit()
        self._refresh_themes(preferred=new_name)

    def _delete_selected_theme(self) -> None:
        selected = self._current_selected_name()
        selected_path = self._selected_theme_path()
        if (
            selected is None
            or selected_path is None
            or not self._is_user_theme(selected_path)
        ):
            self._cancel_delete_confirm()
            return

        try:
            selected_path.unlink()
        except OSError:
            return

        if self._autoload_name == selected:
            self._set_autoload_name(PATH_DEFAULT_THEME.stem)

        if self._applied_name == selected:
            cast(Any, self.window()).set_theme(PATH_DEFAULT_THEME.stem, persist=False)
            self._applied_name = self._read_applied_name()
        self._cancel_delete_confirm()
        self._refresh_themes(preferred=self._applied_name)

    def _open_selected_location(self) -> None:
        if (theme_path := self._selected_theme_path()) is None:
            return
        if not theme_path.exists():
            self._refresh_themes()
            return

        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(theme_path)])
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(theme_path.parent)))

    def _on_config_loaded(self) -> None:
        self._autoload_name = self._read_autoload_name()
        self._autoload_enabled = self._read_autoload_enabled()
        self._applied_name = self._read_applied_name()
        self._refresh_themes(preferred=self._autoload_name)
