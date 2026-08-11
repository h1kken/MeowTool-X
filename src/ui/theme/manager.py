from __future__ import annotations

import typing as t

import json5
from pathlib import Path
from collections import defaultdict

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QLayout, QWidget

from src.app.paths import PATH_DEFAULT_THEME, PATH_THEMES_USER
from src.config import ConfigKey as CKey
from src.utils.logging import logger

from .handlers import QT_HANDLERS
from .parsers import QSS_PARSERS
from .resolvers import resolve_theme
from .helpers import resolve_qt_target
from .types import ThemeMap

if t.TYPE_CHECKING:
    from src.config import Config


class ThemeManager(QObject):
    themeLoaded = Signal()
    
    def __init__(self, config: Config) -> None:
        super().__init__()
        self._window: QWidget | None = None
        self._config = config
                
        self._path = PATH_DEFAULT_THEME

    def set_window(self, window: QWidget):
        self._window = window

    @property
    def path(self) -> Path:
        return self._path

    @property
    def window(self) -> QWidget:
        if self._window is None:
            raise RuntimeError('Window is not initialized')
        return self._window

    def load(self, name: str | None = None) -> None:
        if name is None:
            name = str(self._config.get(CKey.GENERAL_THEME)).strip()
        
        path = PATH_THEMES_USER / f'{name}.json5'
        if not path.is_file():
            logger.warning(f'Can\'t load theme: {path}: file not found, fallback to default')
            path = PATH_DEFAULT_THEME
        
        try:
            with path.open('r', encoding='utf-8') as f:
                resolved = resolve_theme(t.cast(ThemeMap, json5.loads(f.read())))

            self._path = path
            self._apply(resolved)
            self.themeLoaded.emit()
        except (OSError, ValueError) as e:
            logger.error(f'Can\'t load theme {path}: {e}')
        
    def _apply(self, theme: ThemeMap) -> None:
        self.window.setStyleSheet(self._build_qss(theme))
        self._reset_qt()
        self._apply_qt(theme)

    def _build_qss(self, theme: ThemeMap) -> str:
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


    def _reset_qt(self) -> None:
        for layout in self.window.findChildren(QLayout):
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignmentFlag(0))

        for widget in self.window.findChildren(QWidget):
            setter = getattr(widget, 'setAlignment', None)
            if callable(setter):
                setter(Qt.AlignmentFlag(0))


    def _apply_qt(self, theme: ThemeMap) -> None:
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
                        handler(obj, styles)
