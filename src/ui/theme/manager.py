from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
import typing as t

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QLayout, QWidget

import src.ui.theme.files as theme_files
from src.app.paths import PATH_DEFAULT_THEME
from src.ui.theme.parser import ThemeMap, normalize_theme_payload
from src.ui.theme.qss import build_rules
from src.ui.theme.targets import (
    normalize_qss_target,
    parse_qss_target,
    parse_selector_chain,
    resolve_target_widgets,
)
from src.utils.conversion import as_dict

if t.TYPE_CHECKING:
    from src.config import Config


_NO_ALIGNMENT = Qt.AlignmentFlag(0)
_DEFAULT_ALIGNMENT = (
    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
)



class ThemeManager(QObject):
    themeLoaded = Signal(object)
    
    def __init__(self, window: QWidget, config: Config) -> None:
        super().__init__()
        self._window = window
        self._config = config
        
        self._path = PATH_DEFAULT_THEME
        self._data: ThemeMap = {}
        self._defaults: ThemeMap = default_theme()

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def path(self) -> Path:
        return self._path

    @property
    def data(self) -> ThemeMap:
        return self._data

    @property
    def defaults(self) -> ThemeMap:
        return self._defaults

    def load(self, name: str | None = None) -> Path | None:
        loaded = theme_files.load(self._config, name)
        if loaded is None:
            self.themeLoaded.emit(loaded)
            return None

        path, payload = loaded
        self._window.setStyleSheet(self.build(payload, theme_dir=path.parent))
        
        self._path = path
        self.themeLoaded.emit(loaded)
        return path

    def build(self, payload: ThemeMap, *, theme_dir: Path) -> str:
        theme = normalize_theme_payload(payload, include_animations=False)
        widgets = t.cast(dict[str, ThemeMap], as_dict(theme.get('widgets')) or {})
        blocks: list[str] = []

        self._reset_alignments()
        for target, styles in sorted(widgets.items(), key=self._sort_key):
            self._apply_alignments(target, styles)
            blocks.extend(self._build_target(target, styles, theme_dir))

        return '\n\n'.join(blocks)

    def _reset_alignments(self) -> None:
        for widget in (self._window, *self._window.findChildren(QWidget)):
            self._set_widget_alignment(widget, _DEFAULT_ALIGNMENT)
            
            layout = widget.layout()
            if layout is not None:
                self._reset_layout_alignment(layout)

    def _reset_layout_alignment(self, layout: QLayout) -> None:
        layout.setAlignment(_NO_ALIGNMENT)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item is None:
                continue
            item.setAlignment(_NO_ALIGNMENT)
            child_layout = t.cast(QLayout | None, item.layout())
            if child_layout is not None:
                self._reset_layout_alignment(child_layout)

    def _apply_alignments(self, target: str, styles: ThemeMap) -> None:
        content_alignment = self._content_alignment(styles)
        layout_alignment = self._section_alignment(styles, 'layout')
        item_alignment = self._section_alignment(styles, 'layout_item', 'layout-item')
        if all(alignment is None for alignment in (content_alignment, layout_alignment, item_alignment)):
            return

        widgets = resolve_target_widgets(self._window, target, include_window=True)
        for widget in widgets:
            if content_alignment is not None:
                self._set_widget_alignment(widget, content_alignment)

            layout = widget.layout()
            if layout_alignment is not None and layout is not None:
                layout.setAlignment(layout_alignment)

            if item_alignment is not None:
                parent_layout = self._find_parent_layout(widget)
                if parent_layout is not None:
                    parent_layout.setAlignment(widget, item_alignment)

    def _content_alignment(self, styles: ThemeMap) -> Qt.AlignmentFlag | None:
        content = as_dict(styles.get('content')) or {}
        value = self._first_value(content, 'align', 'alignment')
        if value is None:
            value = self._first_value(styles, 'align', 'alignment')
        return self._parse_alignment(value)

    def _section_alignment(self, styles: ThemeMap, *section_names: str) -> Qt.AlignmentFlag | None:
        for section_name in section_names:
            section = as_dict(styles.get(section_name))
            if section is None:
                continue
            value = self._first_value(section, 'align', 'alignment')
            if value is not None:
                return self._parse_alignment(value)
        return None

    @staticmethod
    def _first_value(data: ThemeMap, *keys: str) -> object | None:
        for key in keys:
            if key in data:
                return data[key]
        return None

    def _parse_alignment(self, value: object) -> Qt.AlignmentFlag | None:
        if isinstance(value, int) and not isinstance(value, bool):
            return Qt.AlignmentFlag(value)

        if isinstance(value, list):
            values: list[object] | tuple[object, ...] = t.cast(list[object], value)
        elif isinstance(value, tuple):
            values = t.cast(tuple[object, ...], value)
        else:
            values = (value,)
            
        alignment = _NO_ALIGNMENT
        matched = False

        for value in values:
            if not isinstance(value, str):
                continue
            for token in re.split(r'[\s|,+]+', value.strip().lower()):
                key = token.replace('-', '').replace('_', '')
                flag = _ALIGNMENT_FLAGS.get(key)
                if flag is None:
                    continue
                alignment |= flag
                matched = True

        return alignment if matched else None

    @staticmethod
    def _set_widget_alignment(widget: QWidget, alignment: Qt.AlignmentFlag) -> None:
        setter = getattr(widget, 'setAlignment', None)
        if callable(setter):
            setter(alignment)

    @classmethod
    def _find_parent_layout(cls, widget: QWidget) -> QLayout | None:
        parent = widget.parentWidget()
        while parent is not None:
            layout = parent.layout()
            if layout is not None:
                owner = cls._find_item_layout(layout, widget)
                if owner is not None:
                    return owner
            parent = parent.parentWidget()
        return None

    @classmethod
    def _find_item_layout(cls, layout: QLayout, widget: QWidget) -> QLayout | None:
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item is None:
                continue
            if item.widget() is widget:
                return layout
            child_layout = t.cast(QLayout | None, item.layout())
            if child_layout is not None:
                owner = cls._find_item_layout(child_layout, widget)
                if owner is not None:
                    return owner
        return None

    def _build_target(self, target: str, styles: ThemeMap, theme_dir: Path) -> list[str]:
        if not self._needs_concrete_widgets(target, styles):
            return self._build_blocks((self._selector(target),), styles, theme_dir)

        blocks: list[str] = []
        for widget in resolve_target_widgets(self._window, target, include_window=True):
            name = widget.objectName().strip()
            if not name:
                continue
            resolved = self._resolve_percent_radius(styles, widget)
            blocks.extend(self._build_blocks((f'#{name}',), resolved, theme_dir))
        return blocks

    def _build_blocks(self, selectors: tuple[str, ...], styles: ThemeMap, theme_dir: Path) -> list[str]:
        rules = build_rules(styles, theme_dir)
        if not rules:
            return []

        body = '\n  '.join(rules)
        return [f'{selector} {{\n  {body}\n}}' for selector in selectors if selector]

    def _selector(self, target: str) -> str:
        normalized = normalize_qss_target(target)
        if normalized.startswith(('*', 'MT')):
            return normalized
        return f'#{normalized}'

    def _needs_concrete_widgets(self, target: str, styles: ThemeMap) -> bool:
        parsed = parse_qss_target(target)
        base = parsed[0] if parsed else target
        return (
            parse_selector_chain(target) is not None
            or (base != '*' and any(token in base for token in ('*', '?')))
            or self._has_percent_radius(styles)
        )

    def _has_percent_radius(self, styles: ThemeMap) -> bool:
        for section in ('background', 'border'):
            data = as_dict(styles.get(section))
            radius = None if data is None else data.get('radius')
            if isinstance(radius, str) and radius.strip().endswith('%'):
                return True
        return False

    def _resolve_percent_radius(self, styles: ThemeMap, widget: QWidget) -> ThemeMap:
        resolved = deepcopy(styles)
        base_size = self._radius_base_size(widget)
        if base_size <= 0:
            return resolved

        for section in ('background', 'border'):
            data = as_dict(resolved.get(section))
            if data is None:
                continue
            radius = data.get('radius')
            if not isinstance(radius, str) or not radius.strip().endswith('%'):
                continue
            try:
                percent = float(radius.strip()[:-1])
            except ValueError:
                continue
            value = min(max(base_size * percent / 100.0, 0.0), base_size / 2.0)
            data['radius'] = f'{value:g}px'
        return resolved

    @staticmethod
    def _radius_base_size(widget: QWidget) -> int:
        candidates = (
            widget.size(),
            widget.sizeHint(),
            widget.minimumSizeHint(),
            widget.minimumSize(),
        )
        sizes = [
            min(size.width(), size.height())
            for size in candidates
            if size.width() > 1 and size.height() > 1
        ]
        return min(sizes) if sizes else 0

    @staticmethod
    def _sort_key(item: tuple[str, t.Any]) -> tuple[int, int]:
        target, _styles = item
        if target == '*':
            return 0, 0
        if parse_selector_chain(target) is not None:
            return 3, 0
        parsed = parse_qss_target(target)
        base, properties = parsed if parsed else (target, [])
        if base.startswith('MT'):
            return 1, len(properties)
        return 2, len(properties)
