from __future__ import annotations

import typing as t

import json5
from pathlib import Path
from collections import defaultdict

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLayout, QWidget, QPushButton

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_USER
from src.config import ConfigKey as CKey
from src.utils.filesystem.file import FS
from src.utils.logging import logger
from src.core.types import DataMap

from .handlers import QT_HANDLERS
from .parsers import QSS_PARSERS
from .resolvers import resolve_theme
from .helpers import resolve_qt_target
from .constants import DEFAULT_CONTENT_MARGINS, DEFAULT_SPACING, DEFAULT_ALIGNMENT, DEFAULT_SIZE_POLICIES

if t.TYPE_CHECKING:
    from src.config import Config


class ThemeManager(QObject):
    themeLoaded = Signal()
    
    def __init__(self, config: Config) -> None:
        super().__init__()
        self._window: QWidget | None = None
        self._config = config
        
        self._applied_qt: dict[QObject, set[str]] = defaultdict(set)
        
        self._path = PATH_DEFAULT_THEME

    def set_window(self, window: QWidget):
        self._window = window

    @property
    def path(self) -> Path:
        return self._path

    @property
    def window(self) -> QWidget:
        if self._window is None:
            raise RuntimeError('Window is not linked')
        return self._window

    def load(self, name: str | None = None) -> None:
        if name is None:
            name = self._config.get(CKey.GENERAL_THEME, str)
        
        path = PATH_THEMES_USER / f'{name}.json5'
        if not path.is_file():
            logger.warning(f'Can\'t load theme: {path}: file not found, fallback to default')
            path = PATH_DEFAULT_THEME
        
        try:
            with path.open('r', encoding='utf-8') as f:
                resolved = resolve_theme(t.cast(DataMap, json5.loads(f.read())))

            self._path = path
            self._apply(resolved)
            self.themeLoaded.emit()
        except (OSError, ValueError) as e:
            logger.error(f'Can\'t load theme {path}: {e}')
        
    def create(self, name: str, *, overwrite: bool = False) -> None:
        path = PATH_THEMES_USER / f'{name}.json5'
        if path.is_file() and not overwrite:
            return

        FS.ensure_dir(PATH_THEMES_USER)
        try:
            FS.copy_file(self._path, path, overwrite=overwrite)
        except OSError as e:
            logger.exception(f'Can\'t create theme \'{name}\': {e}')
        
    def rename(self, old_name: str, new_name: str) -> bool:
        old_path = PATH_THEMES_USER / f'{old_name}.json5'
        new_path = PATH_THEMES_USER / f'{new_name}.json5'
        if (
            old_path == new_path
            or old_path.is_file()
            or new_path.is_file()
        ):
            return False

        try:
            old_path.rename(new_path)
            self._path = new_path
            return True
        except OSError as e:
            logger.exception(f'Can\'t rename theme \'{old_name}\' to \'{new_name}\': {e}')
            return False
        
    def _apply(self, theme: DataMap) -> None:
        self.window.setStyleSheet(self._build_qss(theme))
        self._reset_qt()
        self._apply_qt(theme)

    def _build_qss(self, theme: DataMap) -> str:
        widgets = theme.get('widgets')
        if not isinstance(widgets, list):
            return ''

        groups: defaultdict[tuple[str, ...], list[str]] = defaultdict(list)

        for item in widgets:
            if not isinstance(item, dict):
                continue

            targets = item.get('targets')
            styles = item.get('styles')
            if not isinstance(targets, list) or not isinstance(styles, dict):
                continue

            declarations = tuple(
                declaration
                    for handler in QSS_PARSERS
                        for declaration in handler(styles)
            )
            if not declarations:
                continue

            for target in targets:
                if isinstance(target, str) and target.strip():
                    groups[declarations].append(target.strip())

        return '\n\n'.join(
            f'{', '.join(dict.fromkeys(targets))} {{\n'
            + ''.join(f'    {declaration}\n' for declaration in declarations)
            + '}'
            for declarations, targets in groups.items()
        )

    def _apply_qt(self, theme: DataMap) -> None:
        widgets = theme.get('widgets')
        if not isinstance(widgets, list):
            return

        for rule in widgets:
            if not isinstance(rule, dict):
                continue

            targets = rule.get('targets')
            if not isinstance(targets, list):
                continue

            styles = rule.get('styles')
            if not isinstance(styles, dict):
                continue

            for target in targets:
                if not isinstance(target, str):
                    continue

                for obj in resolve_qt_target(self.window, target):
                    for handler in QT_HANDLERS:
                        handler(obj, styles, storage=self._applied_qt)

    def _reset_qt(self) -> None:
        for obj, props in self._applied_qt.items():
            # Same
            if 'alignment' in props:
                setter = getattr(obj, 'setAlignment', None)
                if callable(setter):
                    setter(DEFAULT_ALIGNMENT)
            
            # QLayout || QWidget
            if isinstance(obj, QLayout):
                if 'margin' in props:
                    obj.setContentsMargins(*DEFAULT_CONTENT_MARGINS)
                    
                if 'spacing' in props:
                    obj.setSpacing(DEFAULT_SPACING)

            elif isinstance(obj, QWidget):
                if 'icon' in props:
                    if isinstance(obj, QPushButton):
                        obj.setIcon(QIcon())
                        
                if 'size_policy' in props:
                    obj.setSizePolicy(*DEFAULT_SIZE_POLICIES)

        self._applied_qt.clear()
