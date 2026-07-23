from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QFileSystemWatcher, QSignalBlocker, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLayout, QSizePolicy, QStackedWidget

import src.app.context as ctx
from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_SRC, PATH_THEMES_USER
from src.config.constants import CONFIGS_REFRESH_DEBOUNCE_MS
from src.theme import files as theme_files
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import (
    MTButton,
    MTInlineEditorStack,
    MTLabel,
    MTLabeledList,
    MTLineEdit,
    MTPlainLabel,
    MTWidget,
)
from src.utils.filesystem import FS
from src.utils.filesystem.constants import FILENAME_SPECIAL_CHARS


class SettingsThemePage(MTWidget):
    def __init__(self) -> None:
        super().__init__()
        self._config = ctx.services.config
        self._themes: dict[str, Path] = {}
        self._loaded_name = self._configured_name()

        FS.ensure_dir(PATH_THEMES_USER)
        self._build_ui()

        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(PATH_THEMES_USER))
        self._watcher.directoryChanged.connect(self._queue_refresh)
        
        self._refresh_timer = QTimer(self, singleShot=True, interval=CONFIGS_REFRESH_DEBOUNCE_MS)

        self._refresh_timer.timeout.connect(self._refresh)
        self._themes_list.currentItemChanged.connect(self._sync_actions)
        self._load_button.clicked.connect(self._load_selected)
        
        self._create_button.clicked.connect(self._start_create)
        self._create_line.returnPressed.connect(self._create)
        self._create_cancel.clicked.connect(self._cancel_create)
        
        self._rename_button.clicked.connect(self._start_rename)
        self._rename_line.returnPressed.connect(self._rename)
        self._rename_cancel.clicked.connect(self._cancel_rename)
        
        self._delete_button.clicked.connect(self._confirm_delete)
        self._delete_confirm.clicked.connect(self._delete)
        self._delete_cancel.clicked.connect(self._cancel_delete)
        
        self._open_button.clicked.connect(self._open_location)
        self._config.config_loaded.connect(self._config_loaded)

        self._refresh(preferred=self._loaded_name)

    def _build_ui(self) -> None:
        main_layout = create_layout(LayoutType.VBOX, parent=self)
        content = MTWidget(obj_name="Theme_Page_Widget")
        main_layout.addWidget(content)

        body = create_layout(LayoutType.HBOX, parent=content)
        self._list_column = MTLabeledList(
            obj_name="Theme_List_Column",
            list_obj_name="Theme_List",
        )
        self._themes_list = self._list_column.list_widget
        actions = MTWidget(obj_name="Theme_Actions_Column")
        body.addWidget(self._list_column)
        body.addWidget(actions)

        layout = create_layout(LayoutType.VBOX, parent=actions)
        self._selected_value = self._add_info_row(
            layout,
            "SLCTD",
            "Theme_Selected_Info",
            "Theme_Selected_Label",
            "Theme_Selected_Value",
        )
        self._loaded_value = self._add_info_row(
            layout,
            "LDD",
            "Theme_Loaded_Info",
            "Theme_Loaded_Label",
            "Theme_Loaded_Value",
        )

        self._load_button = MTButton(tr_key="LOAD", obj_name="Theme_Apply_Button")
        self._create_stack = self._editor_stack("create", "CREATE")
        self._rename_stack = self._editor_stack("rename", "RENAME")
        self._delete_stack = self._delete_stack_widget()
        self._open_button = MTButton(
            tr_key="OPN_FL_LCTN",
            obj_name="Theme_Open_Location_Button",
        )

        for widget in (
            self._load_button,
            self._create_stack,
            self._rename_stack,
            self._delete_stack,
            self._open_button,
        ):
            layout.addWidget(widget)
        layout.addStretch()

    def _add_info_row(
        self,
        layout: QLayout,
        tr_key: str,
        row_name: str,
        label_name: str,
        value_name: str,
    ) -> MTPlainLabel:
        row = MTWidget(obj_name=row_name)
        row_layout = create_layout(LayoutType.HBOX, parent=row)
        label = MTLabel(tr_key=tr_key, obj_name=label_name)
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        value = MTPlainLabel("-", obj_name=value_name)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(label)
        row_layout.addWidget(value, stretch=1)
        layout.addWidget(row)
        return value

    def _editor_stack(self, mode: str, tr_key: str) -> QStackedWidget:
        title = mode.capitalize()
        stack = MTInlineEditorStack()
        stack.setObjectName(f"Theme_{title}_Stack")
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        button = MTButton(tr_key=tr_key, obj_name=f"Theme_{title}_Button")
        row = MTWidget(obj_name=f"Theme_{title}_Editor_Row")
        row_layout = create_layout(LayoutType.HBOX, parent=row)
        line = MTLineEdit(obj_name=f"Theme_{title}_Editor_LineEdit")
        line.setPlaceholderText("Theme name")
        cancel = MTButton(tr_key="✕", obj_name=f"Theme_{title}_Editor_Cancel_Button")
        cancel.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(line, 1)
        row_layout.addWidget(cancel)
        stack.addWidget(button)
        stack.addWidget(row)

        if mode == "create":
            self._create_button = button
            self._create_line = line
            self._create_cancel = cancel
        else:
            self._rename_button = button
            self._rename_line = line
            self._rename_cancel = cancel
        return stack

    def _delete_stack_widget(self) -> QStackedWidget:
        stack = MTInlineEditorStack()
        stack.setObjectName("Theme_Delete_Stack")
        self._delete_button = MTButton(tr_key="DELETE", obj_name="Theme_Delete_Button")
        row = MTWidget(obj_name="Theme_Delete_Confirm_Row")
        layout = create_layout(LayoutType.HBOX, parent=row)
        self._delete_confirm = MTButton(
            tr_key="CONFIRM",
            obj_name="Theme_Delete_Confirm_Button",
        )
        self._delete_cancel = MTButton(
            tr_key="✕",
            obj_name="Theme_Delete_Cancel_Button",
        )
        self._delete_cancel.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self._delete_confirm, 1)
        layout.addWidget(self._delete_cancel)
        stack.addWidget(self._delete_button)
        stack.addWidget(row)
        return stack

    def _configured_name(self) -> str:
        value = self._config.get("General>Theme")
        return theme_files.normalize_name(str(value)) or PATH_DEFAULT_THEME.stem

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
        self._selected_value.setText(selected or "-")
        self._loaded_value.setText(self._loaded_name or "-")
        self._load_button.setEnabled(selected is not None)
        self._rename_stack.setEnabled(user_theme)
        self._delete_stack.setEnabled(user_theme)
        self._open_button.setEnabled(selected is not None)
        if not user_theme:
            self._cancel_rename()
            self._cancel_delete()

    def _load(self, name: str, *, persist: bool) -> bool:
        path = ctx.services.theme_manager.load(name)
        if path is None:
            return False
        ctx.services.animation_manager.load(path.stem)
        self._loaded_name = path.stem
        if persist:
            self._config.set("General>Theme", path.stem, force_save=True)
        self._sync_actions()
        return True

    def _load_selected(self) -> None:
        name = self._selected_name()
        if name:
            self._load(name, persist=True)

    def _normalize_new_name(self, value: str) -> str:
        name = theme_files.normalize_name(value)
        if (
            not name
            or name.startswith(".")
            or any(char in name for char in FILENAME_SPECIAL_CHARS)
        ):
            return ""
        return name

    def _start_create(self) -> None:
        self._create_line.clear()
        self._create_stack.setCurrentIndex(1)
        self._create_line.setFocus()

    def _cancel_create(self) -> None:
        self._create_line.clear()
        self._create_stack.setCurrentIndex(0)

    def _create(self) -> None:
        name = self._normalize_new_name(self._create_line.text())
        if not name or theme_files.find(PATH_THEMES_USER, name) is not None:
            return
        path = theme_files.output_path(PATH_THEMES_USER, name)
        selected = self._selected_path()
        payload: dict[str, Any] = (
            theme_files.read_safe(selected)
            if selected is not None
            else {"widgets": []}
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
        self._rename_line.setText(name)
        self._rename_stack.setCurrentIndex(1)
        self._rename_line.setFocus()
        self._rename_line.selectAll()

    def _cancel_rename(self) -> None:
        self._rename_line.clear()
        self._rename_stack.setCurrentIndex(0)

    def _rename(self) -> None:
        old_name = self._selected_name()
        old_path = self._selected_path()
        new_name = self._normalize_new_name(self._rename_line.text())
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
            self._load(new_name, persist=True)
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
            self._load(PATH_DEFAULT_THEME.stem, persist=True)
        self._cancel_delete()
        self._refresh(preferred=self._loaded_name)

    def _open_location(self) -> None:
        path = self._selected_path()
        if path is None or not path.exists():
            self._refresh()
            return
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _config_loaded(self) -> None:
        self._loaded_name = self._configured_name()
        self._refresh(preferred=self._loaded_name)
