from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from src.theme.qss.builder import QssBuilder
from src.theme.qss.targets import (
    normalize_qss_target,
    parse_qss_target,
    parse_selector_chain,
    resolve_target_widgets,
)
from src.theme.schema.access import theme_map
from src.theme.schema.payload import (
    deep_merge_dicts,
    merge_widget_theme_data,
    normalize_theme_payload,
)
from src.theme.schema.types import ThemeMap
from src.theme.storage.io import load_theme_payload
from src.theme.types import ThemeChangePayload, ThemeWidgetsMap

if TYPE_CHECKING:
    from src.config.manager import Config


class ThemeManager(QObject):
    theme_changed = Signal(dict, dict)

    def __init__(
        self,
        window: QWidget,
        config: Config,
        *,
        emit_theme_changed: bool = True,
    ) -> None:
        super().__init__()
        self._window = window
        self.config = config
        
        self._default_theme: ThemeMap = deepcopy(default_theme) if default_theme is not None else {}
        self._current_theme: ThemeMap = normalize_theme_payload(self._default_theme)

        self._qss_builder = QssBuilder()
        self._qss_builder.font_ready.connect(self._on_async_font_ready)

        self._theme_base_dir: Path | None = None
        self._theme_change_suppressed = False
        self._pending_theme_change: ThemeChangePayload | None = None
        self._last_emitted_theme_change: ThemeChangePayload | None = None
        self._emit_theme_changed_enabled = bool(emit_theme_changed)

    @property
    def current_theme(self) -> ThemeMap:
        return deepcopy(self._current_theme)

    def current_theme_widgets(self) -> ThemeWidgetsMap:
        return deepcopy(self._theme_widgets())

    def load(self, theme: Path | ThemeMap, *, merge_with_default: bool = False) -> None:
        if isinstance(theme, Path):
            self._theme_base_dir = theme.parent
            self._qss_builder.set_theme_base_dir(self._theme_base_dir)
            loaded_theme = load_theme_payload(theme)
        else:
            self._theme_base_dir = None
            self._qss_builder.set_theme_base_dir(None)
            loaded_theme = theme

        if merge_with_default:
            default_theme = normalize_theme_payload(self._default_theme)
            user_theme = normalize_theme_payload(loaded_theme)
            merged_theme = deep_merge_dicts(
                {key: value for key, value in default_theme.items() if key != 'widgets'},
                {key: value for key, value in user_theme.items() if key != 'widgets'},
            )
            merged_widgets: ThemeWidgetsMap = deepcopy(self._theme_widgets(default_theme))
            user_widgets = self._theme_widgets(user_theme)

            for target, styles in user_widgets.items():
                merged_widgets[target] = merge_widget_theme_data(merged_widgets.get(target), styles)

            merged_theme['widgets'] = merged_widgets
            self._current_theme = merged_theme
            return

        self._current_theme = normalize_theme_payload(loaded_theme)

    def apply(self) -> None:
        qss_parts, animations, styles_by_widget = self._build_theme_application(
            self._window,
            include_window=True,
            skip_empty_targets=False,
            collect_animations=True,
        )
        self._clear_helper_properties(self._window)
        self._apply_helper_properties(styles_by_widget)
        self._window.setStyleSheet('\n'.join(qss_parts))
        self._emit_theme_changed(animations, deepcopy(self._theme_widgets()))

    def apply_to_subtree(self, root: QWidget) -> None:
        qss_parts, _animations, styles_by_widget = self._build_theme_application(
            root,
            include_window=False,
            skip_empty_targets=True,
            collect_animations=False,
        )
        self._clear_helper_properties(root)
        self._apply_helper_properties(styles_by_widget)
        root.setStyleSheet('\n'.join(qss_parts))

    def suppress_theme_changed(self) -> None:
        self._theme_change_suppressed = True

    def resume_theme_changed(self, *, flush: bool = False) -> None:
        self._theme_change_suppressed = False
        if flush and self._pending_theme_change is not None:
            animations, widgets = self._pending_theme_change
            self._pending_theme_change = None
            self._emit_theme_changed(animations, widgets)

    def _on_async_font_ready(self, _source: str) -> None:
        self.apply()

    def _emit_theme_changed(self, animations: ThemeMap, theme_widgets: ThemeWidgetsMap) -> None:
        if not self._emit_theme_changed_enabled:
            self._pending_theme_change = None
            return

        payload = (deepcopy(animations), deepcopy(theme_widgets))
        if self._theme_change_suppressed:
            self._pending_theme_change = payload
            return

        if self._last_emitted_theme_change is None and not payload[0] and not payload[1]:
            self._pending_theme_change = None
            return

        if payload == self._last_emitted_theme_change:
            self._pending_theme_change = None
            return

        self._pending_theme_change = None
        self._last_emitted_theme_change = deepcopy(payload)
        self.theme_changed.emit(*payload)

    def _build_theme_application(
        self,
        root: QWidget,
        *,
        include_window: bool,
        skip_empty_targets: bool,
        collect_animations: bool,
    ) -> tuple[list[str], ThemeMap, dict[QWidget, ThemeMap]]:
        qss_parts: list[str] = []
        animations: ThemeMap = {}
        styles_by_widget: dict[QWidget, ThemeMap] = {}

        widget_items = list(self._theme_widgets().items())
        for index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            _ = index
            qss_target = normalize_qss_target(target)
            effective_styles = self._qss_styles(styles, qss_target)
            widgets = resolve_target_widgets(root, target, include_window=include_window)
            if skip_empty_targets and not widgets:
                continue

            for widget in widgets:
                styles_by_widget[widget] = merge_widget_theme_data(styles_by_widget.get(widget), effective_styles)

            if collect_animations and isinstance(styles.get('animations'), (dict, list)):
                animations[target] = deepcopy(cast(dict[str, Any] | list[Any], styles['animations']))

            selector = '' if qss_target.startswith(('*', 'MT')) else '#'
            qss = self._build_qss(qss_target, effective_styles, selector, widgets=widgets)
            if qss:
                qss_parts.append(qss)

        return qss_parts, animations, styles_by_widget

    def _qss_styles(self, styles: ThemeMap, qss_target: str) -> ThemeMap:
        if qss_target == '*' and theme_map(styles.get('media')) is not None:
            return {key: value for key, value in styles.items() if key != 'media'}
        return styles

    def _apply_helper_properties(self, styles_by_widget: dict[QWidget, ThemeMap]) -> None:
        for widget, styles in styles_by_widget.items():
            resolved_styles = (
                cast(ThemeMap, self._qss_builder.resolve_relative_styles(styles, widget))
                if self._qss_builder.contains_resolvable_radius(styles) else
                styles
            )
            self._apply_widget_helper_properties(widget, resolved_styles)

    def _apply_widget_helper_properties(self, widget: QWidget, styles: ThemeMap) -> None:
        background = theme_map(styles.get('background'))
        border = theme_map(styles.get('border'))

        background_rule = self._qss_builder.build_background_color(None if background is None else background.get('color'))
        border_rule = self._qss_builder.build_border(border) if border is not None else None

        radius_source = None
        if border is not None and border.get('radius') is not None:
            radius_source = border.get('radius')
        elif background is not None:
            radius_source = background.get('radius')
        radius_value = self._qss_builder.normalize_measure(radius_source)

        padding_rule = self._qss_builder.build_padding_rule(styles)
        padding_box = self._qss_builder.normalize_box_from_mapping(styles, 'padding')

        self._set_widget_property_if_changed(widget, '_themeBackgroundRule', background_rule)
        self._set_widget_property_if_changed(widget, '_themeBorderRule', border_rule)
        self._set_widget_property_if_changed(widget, '_themeBorderRadius', radius_value)
        self._set_widget_property_if_changed(widget, '_themePaddingRule', padding_rule)
        self._set_widget_property_if_changed(widget, '_themePaddingBox', padding_box)

    def _clear_helper_properties(self, root: QWidget) -> None:
        for widget in [root, *root.findChildren(QWidget)]:
            self._qss_builder.clear_theme_helper_properties(widget)

    def _set_widget_property_if_changed(self, widget: QWidget, name: str, value: object) -> bool:
        if widget.property(name) == value:
            return False
        widget.setProperty(name, value)
        return True

    def _theme_widgets(self, theme: ThemeMap | None = None) -> ThemeWidgetsMap:
        source = self._current_theme if theme is None else theme
        return cast(ThemeWidgetsMap, theme_map(source.get('widgets')) or {})

    def _theme_widget_sort_key(self, item: tuple[int, tuple[str, Any]]) -> tuple[int, int, int]:
        index, (target, _styles) = item
        return (*self._target_apply_priority(target), index)

    def _target_apply_priority(self, target: str) -> tuple[int, int]:
        text = str(target).strip()
        if not text:
            return 4, 0

        if text == '*':
            return 0, 0

        if chain := parse_selector_chain(text):
            return 3, self._selector_chain_specificity(chain)

        parsed = parse_qss_target(text)
        base_target, properties = parsed if parsed else (text, [])
        if base_target == '*':
            return 0, len(properties)
        if base_target.startswith('MT'):
            return 1, len(properties)
        return 2, self._target_specificity(base_target, properties)

    def _selector_chain_specificity(self, chain: list[tuple[str, str]]) -> int:
        specificity = 0
        for _relation, segment in chain:
            parsed = parse_qss_target(segment)
            if not parsed:
                continue
            base_target, properties = parsed
            specificity += self._target_specificity(base_target, properties)
        return specificity

    def _target_specificity(self, target: str, properties: list[tuple[str, str]]) -> int:
        text = str(target or '')
        wildcard_count = text.count('*') + text.count('?')
        literal_length = len(text.replace('*', '').replace('?', ''))
        return (len(properties) * 10000) + literal_length - (wildcard_count * 1000)

    def _build_qss(
        self,
        obj_name: str,
        styles: ThemeMap,
        selector: str = '#',
        *,
        widgets: list[QWidget] | None = None,
    ) -> str:
        return self._qss_builder.build(
            obj_name,
            styles,
            selector,
            widgets=widgets,
            root_widget=self._window,
        )

