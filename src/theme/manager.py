from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast, TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QSize, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QBoxLayout, QGraphicsDropShadowEffect, QLabel, QLayout, QLineEdit, QScrollArea, QSizePolicy, QWidget

from src.theme.colors import to_qcolor
from src.theme.media.overlay import ThemeMediaOverlay
from src.theme.qss.builder import QssBuilder
from src.theme.qss.normalizer import StyleNormalizer
from src.theme.qss.targets import (
    normalize_qss_target,
    parse_selector_chain,
    parse_qss_target,
    resolve_target_widgets,
)
from src.theme.schema.payload import (
    deep_merge_dicts,
    merge_widget_theme_data,
    normalize_theme_payload,
)
from src.theme.schema.access import coerce_int, theme_map
from src.theme.schema.types import ThemeMap
from src.theme.storage.io import load_theme_payload
from src.theme.types import (
    GeometrySnapshot,
    LayoutSnapshot,
    RuntimeStylesMap,
    ThemeChangePayload,
    ThemeWidgetsMap,
)
from src.ui.widgets.main.inputs import MTLineEdit
from src.ui.widgets.main.box import BoxThemeMixin
from src.ui.widgets.main.checkables import MTSwitch
from src.ui.widgets.main.containers import MTComboBox
from src.ui.widgets.main.inputs import MTSlider
from src.ui.widgets.main.media import MTMediaWidget
from src.ui.widgets.settings.containers import MTCollapsibleContainer

if TYPE_CHECKING:
    from src.config.manager import Config


class ThemeManager(QObject):
    theme_changed = Signal(dict, dict)
    
    def __init__(
        self,
        root: QWidget,
        config: Config,
        default_theme: ThemeMap | None = None,
        *,
        emit_theme_changed: bool = True,
    ) -> None:
        super().__init__()
        self._root = root
        self._default_theme: ThemeMap = deepcopy(default_theme) if default_theme is not None else {}
        self._current_theme: ThemeMap = normalize_theme_payload(self._default_theme)
        
        self._qss_builder = QssBuilder()
        self._qss_builder.font_ready.connect(self._on_async_font_ready)
        
        self._style_normalizer = StyleNormalizer()
        
        self._styled_parts_widgets: set[QWidget] = set()
        self._styled_media_widgets: set[QWidget] = set()
        self._styled_combo_popup_widgets: set[QWidget] = set()
        self._styled_theme_prop_widgets: set[QWidget] = set()
        self._styled_geometry_widgets: dict[QWidget, GeometrySnapshot] = {}
        self._styled_viewport_margin_widgets: dict[QScrollArea, tuple[int, int, int, int]] = {}
        self._styled_size_policy_widgets: dict[QWidget, tuple[QSizePolicy.Policy, QSizePolicy.Policy]] = {}
        self._styled_layout_item_alignment_widgets: dict[QWidget, Qt.AlignmentFlag] = {}
        self._styled_layout_widgets: dict[QWidget, LayoutSnapshot] = {}
        self._styled_text_alignment_widgets: dict[QWidget, int] = {}
        self._styled_effect_widgets: set[QWidget] = set()
        self._styled_button_icon_widgets: dict[QAbstractButton, tuple[QIcon, QSize]] = {}
        self._styled_text_focus_alignment_widgets: set[QWidget] = set()
        self._styled_line_edit_margin_widgets: dict[QWidget, tuple[int, int, int, int]] = {}
        self._styled_line_edit_text_widgets: dict[QWidget, QPalette] = {}
        self._styled_text_font_widgets: dict[QWidget, QFont] = {}
        self._styled_box_widgets: set[QWidget] = set()
        
        self._checkable_state_style_slots: dict[QWidget, Any] = {}
        self._checkable_state_style_base_qss: dict[QWidget, str] = {}
        
        self._media_overlays: dict[QWidget, ThemeMediaOverlay] = {}
        self._media_overlay_filters: set[QWidget] = set()
        
        self._theme_base_dir: Path | None = None
        self._theme_change_suppressed = False
        self._pending_theme_change: ThemeChangePayload | None = None
        self._last_emitted_theme_change: ThemeChangePayload | None = None
        self._emit_theme_changed_enabled = bool(emit_theme_changed)
        

    _ALIGNED_WIDGET_TYPES = (QLabel, QLineEdit, QAbstractSpinBox, MTComboBox)
    _PARTS_THEME_WIDGET_TYPES = (MTSlider, MTSwitch, MTComboBox, MTCollapsibleContainer)

    @property
    def current_theme(self) -> ThemeMap:
        return deepcopy(self._current_theme)

    def current_theme_widgets(self) -> ThemeWidgetsMap:
        return deepcopy(self._theme_widgets())

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if isinstance(obj, QWidget):
            if obj in self._media_overlay_filters:
                overlay = self._media_overlays.get(obj)
                if overlay is not None:
                    if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
                        overlay.sync_geometry()
                        if obj.isVisible() and overlay.has_media():
                            overlay.show()
                    elif event.type() == QEvent.Type.Hide:
                        overlay.hide()
        return super().eventFilter(obj, event)

    def load(self, theme: Path | ThemeMap, *, merge_with_default: bool = False) -> None:
        if isinstance(theme, Path):
            self._theme_base_dir = theme.parent
            self._qss_builder.set_theme_base_dir(self._theme_base_dir)
            theme_map = load_theme_payload(theme)
        else:
            self._theme_base_dir = None
            self._qss_builder.set_theme_base_dir(None)
            theme_map = theme

        if merge_with_default:
            default_theme = normalize_theme_payload(self._default_theme)
            user_theme = normalize_theme_payload(theme_map)
            merged_theme = deep_merge_dicts(
                {key: value for key, value in default_theme.items() if key != 'widgets'},
                {key: value for key, value in user_theme.items() if key != 'widgets'},
            )
            merged_widgets: ThemeWidgetsMap = deepcopy(self._theme_widgets(default_theme))
            user_widgets = self._theme_widgets(user_theme)

            for obj_name, data in user_widgets.items():
                merged_widgets[obj_name] = merge_widget_theme_data(
                    merged_widgets.get(obj_name),
                    data,
                )

            merged_theme['widgets'] = merged_widgets
            self._current_theme = merged_theme
            return

        self._current_theme = normalize_theme_payload(theme_map)

    def apply(self) -> None:
        self._reset_runtime_styles()
        qss_parts, animations = self._build_theme_application(
            self._root,
            include_window=True,
            skip_empty_targets=False,
            collect_animations=True,
        )
        self._root.setStyleSheet('\n'.join(qss_parts))
        self._refresh_bound_checkable_state_widgets()
        self._emit_theme_changed(animations, deepcopy(self._theme_widgets()))

    def apply_to_subtree(self, root: QWidget) -> None:
        qss_parts, _animations = self._build_theme_application(
            root,
            include_window=False,
            skip_empty_targets=True,
            collect_animations=False,
        )
        root.setStyleSheet('\n'.join(qss_parts))
        root.update()

    def _build_theme_application(
        self,
        root: QWidget,
        *,
        include_window: bool,
        skip_empty_targets: bool,
        collect_animations: bool,
    ) -> tuple[list[str], ThemeMap]:
        qss_parts: list[str] = []
        animations: ThemeMap = {}
        runtime_styles_by_widget: RuntimeStylesMap = {}

        widget_items = list(self._theme_widgets().items())
        for _index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            qss_target = normalize_qss_target(target)
            effective_styles: ThemeMap = styles
            if qss_target == '*' and isinstance(styles.get('media'), dict):
                effective_styles = {
                    key: value for key, value in styles.items() if key != 'media'
                }
            widgets = resolve_target_widgets(root, target, include_window=include_window)
            if skip_empty_targets and not widgets:
                continue

            resolved_styles = self._apply_target_runtime_styles(
                target,
                effective_styles,
                widgets,
                runtime_styles_by_widget,
            )
            if collect_animations:
                target_animations = resolved_styles.get('animations')
                if not isinstance(target_animations, (dict, list)):
                    target_animations = styles.get('animations')
                if isinstance(target_animations, (dict, list)):
                    animations[target] = deepcopy(cast(dict[str, Any] | list[Any], target_animations))

            selector = '' if qss_target.startswith(('*', 'MT')) else '#'
            qss_styles = self._strip_checkable_state_styles(resolved_styles)
            qss = self._build_qss(qss_target, qss_styles, selector, widgets=widgets)
            if qss:
                qss_parts.append(qss)

        return qss_parts, animations

    def _apply_target_runtime_styles(
        self,
        target: str,
        styles: ThemeMap,
        widgets: list[QWidget],
        runtime_styles_by_widget: RuntimeStylesMap,
    ) -> ThemeMap:
        style_options, effective_styles = self._extract_style_options(styles)
        if style_options.get('clear') is True:
            self._clear_target_widget_styles(widgets)
            for widget in widgets:
                runtime_styles_by_widget.pop(widget, None)

        for widget in widgets:
            merged_styles = merge_widget_theme_data(
                runtime_styles_by_widget.get(widget),
                effective_styles,
            )
            merged_styles = self._merge_checkable_state_styles(widget, merged_styles)
            runtime_styles_by_widget[widget] = merged_styles
            self._apply_theme_helper_properties(merged_styles, [widget])
            self._apply_runtime_styles(target, merged_styles, widgets=[widget])
            if self._has_checkable_state_styles(effective_styles):
                self._bind_checkable_state_style(widget)

        return effective_styles
    def _on_async_font_ready(self, _source: str) -> None:
        self.apply()

    def suppress_theme_changed(self) -> None:
        self._theme_change_suppressed = True

    def resume_theme_changed(self, *, flush: bool = False) -> None:
        self._theme_change_suppressed = False
        if flush and self._pending_theme_change is not None:
            animations, widgets = self._pending_theme_change
            self._pending_theme_change = None
            self._emit_theme_changed(animations, widgets)

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

    def _theme_widgets(self, theme: ThemeMap | None = None) -> ThemeWidgetsMap:
        source = self._current_theme if theme is None else theme
        return cast(ThemeWidgetsMap, theme_map(source.get('widgets')) or {})

    def _reset_runtime_styles(self) -> None:
        for widget, base_qss in self._checkable_state_style_base_qss.items():
            try:
                widget.setStyleSheet(base_qss)
                widget.updateGeometry()
                widget.update()
            except RuntimeError:
                continue

        for widget in self._styled_theme_prop_widgets:
            try:
                self._style_normalizer.clear_theme_helper_properties(widget)
                widget.update()
            except RuntimeError:
                continue

        for widget, original in self._styled_geometry_widgets.items():
            try:
                widget.setMinimumWidth(int(original['minimum_width']))
                widget.setMaximumWidth(int(original['maximum_width']))
                widget.setMinimumHeight(int(original['minimum_height']))
                widget.setMaximumHeight(int(original['maximum_height']))
            except RuntimeError:
                continue

        for widget, margins in self._styled_viewport_margin_widgets.items():
            try:
                widget.setViewportMargins(*margins)
                widget.viewport().update()
                widget.updateGeometry()
            except RuntimeError:
                continue

        for widget, (horizontal, vertical) in self._styled_size_policy_widgets.items():
            try:
                policy = widget.sizePolicy()
                policy.setHorizontalPolicy(horizontal)
                policy.setVerticalPolicy(vertical)
                widget.setSizePolicy(policy)
                widget.updateGeometry()
            except RuntimeError:
                continue

        for widget, alignment in self._styled_layout_item_alignment_widgets.items():
            try:
                parent = widget.parentWidget()
                layout = parent.layout() if isinstance(parent, QWidget) else None
                if isinstance(layout, QLayout):
                    layout.setAlignment(widget, alignment)
            except RuntimeError:
                continue

        for widget, original in self._styled_layout_widgets.items():
            try:
                if not isinstance((layout := widget.layout()), QLayout):
                    continue
                self._clear_layout_justify(layout, original)
                layout.setContentsMargins(*original['margin'])
                layout.setSpacing(original['spacing'])
                layout.setAlignment(Qt.AlignmentFlag(original['alignment']))
            except RuntimeError:
                continue

        for widget, original_alignment in self._styled_text_alignment_widgets.items():
            try:
                if isinstance(widget, self._ALIGNED_WIDGET_TYPES):
                    widget.setAlignment(Qt.AlignmentFlag(int(original_alignment)))
            except RuntimeError:
                continue

        for widget, original_font in self._styled_text_font_widgets.items():
            try:
                if self._set_font_if_changed(widget, QFont(original_font)):
                    widget.updateGeometry()
                    widget.update()
            except RuntimeError:
                continue

        for widget, (icon, icon_size) in self._styled_button_icon_widgets.items():
            try:
                widget.setIcon(QIcon(icon))
                widget.setIconSize(QSize(icon_size))
                widget.updateGeometry()
                widget.update()
            except RuntimeError:
                continue

        for widget in self._styled_text_focus_alignment_widgets:
            try:
                if isinstance(widget, MTLineEdit):
                    widget.clear_focus_alignments()
            except RuntimeError:
                continue

        for widget, margins in self._styled_line_edit_margin_widgets.items():
            try:
                if isinstance(widget, QLineEdit):
                    widget.setTextMargins(*margins)
                    widget.updateGeometry()
                    widget.update()
            except RuntimeError:
                continue

        for widget, original_palette in self._styled_line_edit_text_widgets.items():
            try:
                widget.setPalette(QPalette(original_palette))
                if isinstance(widget, MTLineEdit):
                    widget.clear_line_edit_text_theme()
                widget.update()
            except RuntimeError:
                continue

        for widget in self._styled_box_widgets:
            try:
                if isinstance(widget, BoxThemeMixin):
                    widget.clear_box_theme()
            except RuntimeError:
                continue

        for widget in self._styled_effect_widgets:
            try:
                widget.setGraphicsEffect(cast(Any, None))
            except RuntimeError:
                continue

        for widget in self._styled_parts_widgets:
            try:
                if isinstance(widget, self._PARTS_THEME_WIDGET_TYPES):
                    widget.reset_theme()
            except RuntimeError:
                continue

        for widget in self._styled_media_widgets:
            try:
                if isinstance(widget, MTMediaWidget):
                    widget.reset_theme()
            except RuntimeError:
                continue

        for widget in self._styled_combo_popup_widgets:
            try:
                if isinstance(widget, MTComboBox):
                    widget.reset_theme()
            except RuntimeError:
                continue

        for overlay in list(self._media_overlays.values()):
            try:
                overlay.reset_theme()
                overlay.deleteLater()
            except RuntimeError:
                continue

        for widget in list(self._media_overlay_filters):
            try:
                widget.removeEventFilter(self)
            except RuntimeError:
                continue

        self._styled_parts_widgets.clear()
        self._styled_media_widgets.clear()
        self._styled_combo_popup_widgets.clear()
        self._styled_theme_prop_widgets.clear()
        self._styled_geometry_widgets.clear()
        self._styled_viewport_margin_widgets.clear()
        self._styled_size_policy_widgets.clear()
        self._styled_layout_item_alignment_widgets.clear()
        self._styled_layout_widgets.clear()
        self._styled_text_alignment_widgets.clear()
        self._styled_effect_widgets.clear()
        self._styled_button_icon_widgets.clear()
        self._styled_text_focus_alignment_widgets.clear()
        self._styled_line_edit_margin_widgets.clear()
        self._styled_line_edit_text_widgets.clear()
        self._styled_text_font_widgets.clear()
        self._styled_box_widgets.clear()
        self._media_overlays.clear()
        self._media_overlay_filters.clear()

    def _refresh_bound_checkable_state_widgets(self) -> None:
        for widget in list(self._checkable_state_style_slots):
            self._refresh_checkable_state_widget(widget)

    def _has_checkable_state_styles(self, styles: ThemeMap) -> bool:
        return theme_map(styles.get('checked')) is not None or theme_map(styles.get('unchecked')) is not None

    def _strip_checkable_state_styles(self, styles: ThemeMap) -> ThemeMap:
        return {
            key: deepcopy(value)
            for key, value in styles.items()
            if key not in {'checked', 'unchecked'}
        }

    def _merge_checkable_state_styles(self, widget: QWidget, styles: ThemeMap) -> ThemeMap:
        merged = self._strip_checkable_state_styles(styles)
        state_styles = theme_map(styles.get('checked')) if self._widget_is_checked(widget) else theme_map(styles.get('unchecked'))
        if state_styles is not None:
            merged = merge_widget_theme_data(merged, state_styles)
        return merged

    def _widget_is_checked(self, widget: QWidget) -> bool:
        if not isinstance(widget, QAbstractButton):
            return False
        try:
            return bool(widget.isCheckable() and widget.isChecked())
        except RuntimeError:
            return False

    def _bind_checkable_state_style(self, widget: QWidget) -> None:
        if widget in self._checkable_state_style_slots or not isinstance(widget, QAbstractButton):
            return

        self._checkable_state_style_base_qss.setdefault(widget, widget.styleSheet())
        def slot(_checked: bool, w: QWidget = widget) -> None:
            QTimer.singleShot(0, lambda: self._refresh_checkable_state_widget(w))

        self._checkable_state_style_slots[widget] = slot
        widget.toggled.connect(slot)

    def _refresh_checkable_state_widget(self, widget: QWidget) -> None:
        try:
            widget.objectName()
        except RuntimeError:
            return

        merged_styles: ThemeMap = {}
        widget_items = list(self._current_theme.get('widgets', {}).items())
        for _index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            styles = cast(ThemeMap, styles)

            if widget not in resolve_target_widgets(self._root, target, include_window=True):
                continue

            qss_target = normalize_qss_target(target)
            effective_styles = styles
            if qss_target == '*' and isinstance(styles.get('media'), dict):
                effective_styles = {key: value for key, value in styles.items() if key != 'media'}

            style_options, effective_styles = self._extract_style_options(effective_styles)
            if style_options.get('clear') is True:
                try:
                    widget.setStyleSheet(self._checkable_state_style_base_qss.get(widget, ''))
                except RuntimeError:
                    return
                merged_styles = {}

            merged_styles = merge_widget_theme_data(merged_styles, effective_styles)

        merged_styles = self._merge_checkable_state_styles(widget, merged_styles)
        self._apply_theme_helper_properties(merged_styles, [widget])
        self._apply_runtime_styles(widget.objectName() or type(widget).__name__, merged_styles, widgets=[widget])

        selector = '#' if widget.objectName() else ''
        qss_target = widget.objectName() or type(widget).__name__
        qss_styles = self._strip_checkable_state_styles(merged_styles)
        qss = self._build_qss(qss_target, qss_styles, selector, widgets=[widget])
        base_qss = self._checkable_state_style_base_qss.get(widget, '')
        try:
            widget.setStyleSheet(f'{base_qss}\n{qss}'.strip())
            widget.updateGeometry()
            widget.update()
        except RuntimeError:
            return

    def _extract_style_options(self, styles: ThemeMap) -> tuple[dict[str, Any], ThemeMap]:
        options: dict[str, Any] = {}
        filtered = dict(styles)
        if 'clear' in filtered:
            options['clear'] = bool(filtered.pop('clear'))
        return options, filtered

    def _clear_target_widget_styles(self, widgets: list[QWidget]) -> None:
        for widget in widgets:
            try:
                self._set_widget_stylesheet_if_changed(widget, '')
                if isinstance(widget, BoxThemeMixin):
                    widget.clear_box_theme()
                widget.update()
            except RuntimeError:
                continue

    def _set_widget_property_if_changed(self, widget: QWidget, name: str, value: object) -> bool:
        if widget.property(name) == value:
            return False
        widget.setProperty(name, value)
        return True

    def _set_widget_stylesheet_if_changed(self, widget: QWidget, stylesheet: str) -> bool:
        if widget.styleSheet() == stylesheet:
            return False
        widget.setStyleSheet(stylesheet)
        return True

    def _set_layout_margins_if_changed(self, layout: QLayout, margins: tuple[int, int, int, int]) -> bool:
        current = layout.contentsMargins()
        current_margins = (current.left(), current.top(), current.right(), current.bottom())
        if current_margins == margins:
            return False
        layout.setContentsMargins(*margins)
        return True

    def _set_layout_alignment_if_changed(self, layout: QLayout, alignment: Qt.AlignmentFlag) -> bool:
        if layout.alignment() == alignment:
            return False
        layout.setAlignment(alignment)
        return True

    def _set_viewport_margins_if_changed(self, widget: QScrollArea, margins: tuple[int, int, int, int]) -> bool:
        current = widget.viewportMargins()
        current_margins = (current.left(), current.top(), current.right(), current.bottom())
        if current_margins == margins:
            return False
        widget.setViewportMargins(*margins)
        return True

    def _set_font_if_changed(self, widget: QWidget, font: QFont) -> bool:
        if widget.font() == font:
            return False
        widget.setFont(font)
        return True

    def _apply_theme_helper_properties(self, styles: ThemeMap, widgets: list[QWidget]) -> None:
        needs_relative_resolution = self._qss_builder.contains_percent_radius(styles)
        for widget in widgets:
            raw_padding_box = self._style_normalizer.normalize_box_from_mapping(styles, 'padding')
            if raw_padding_box is not None:
                self._set_widget_property_if_changed(widget, '_themePaddingBox', raw_padding_box)

            resolved_styles = self._qss_builder.resolve_relative_styles(styles, widget) if needs_relative_resolution else styles
            applied = False

            applied = self._apply_widget_frame_rules(widget, resolved_styles) or applied
            applied = self._apply_line_edit_padding_theme(widget, resolved_styles) or applied

            text_data = theme_map(resolved_styles.get('text'))
            if text_data is not None:
                applied = self._apply_text_font_theme(widget, text_data) or applied
                applied = self._apply_text_alignment_theme(
                    widget,
                    text_data,
                    align_keys=('align', 'alignment'),
                ) or applied
                applied = self._apply_text_focus_alignment_theme(widget, text_data) or applied
                applied = self._apply_line_edit_text_theme(widget, text_data) or applied
                applied = self._apply_button_icon_theme(widget, text_data) or applied
            applied = self._apply_button_icon_theme(widget, resolved_styles) or applied

            if (effects_data := theme_map(resolved_styles.get('effects'))) is not None:
                applied = self._apply_shadow_effect_theme(widget, effects_data) or applied
            if (layout_data := theme_map(resolved_styles.get('layout'))) is not None:
                applied = self._apply_layout_theme(widget, layout_data) or applied
            if (viewport_data := theme_map(resolved_styles.get('viewport'))) is not None:
                applied = self._apply_viewport_theme(widget, viewport_data) or applied
            if (size_data := theme_map(resolved_styles.get('size'))) is not None:
                applied = self._apply_size_theme(widget, size_data) or applied
            if (geometry_data := theme_map(resolved_styles.get('geometry'))) is not None:
                applied = self._apply_geometry_theme(widget, geometry_data) or applied

            if applied:
                self._styled_theme_prop_widgets.add(widget)

    def _apply_widget_frame_rules(self, widget: QWidget, styles: ThemeMap) -> bool:
        applied = False
        background_data = theme_map(styles.get('background'))
        border_data = theme_map(styles.get('border'))

        if background_data is not None:
            if (bg_rule := self._qss_builder.build_background_color(background_data.get('color'))):
                applied = self._set_widget_property_if_changed(widget, '_themeBackgroundRule', bg_rule) or applied
            if border_data is None:
                applied = self._apply_widget_border_radius_rule(widget, background_data.get('radius')) or applied

        if border_data is not None:
            if (border_rule := self._qss_builder.build_border(border_data)):
                applied = self._set_widget_property_if_changed(widget, '_themeBorderRule', border_rule) or applied
            radius = border_data.get('radius', (background_data or {}).get('radius'))
            applied = self._apply_widget_border_radius_rule(widget, radius) or applied

        if (padding_rule := self._qss_builder.build_padding_rule(styles)):
            applied = self._set_widget_property_if_changed(widget, '_themePaddingRule', padding_rule) or applied
            applied = self._set_widget_property_if_changed(
                widget,
                '_themePaddingBox',
                self._style_normalizer.normalize_box_from_mapping(styles, 'padding'),
            ) or applied

        return applied

    def _apply_widget_border_radius_rule(self, widget: QWidget, radius: object) -> bool:
        if radius is None:
            return False
        radius_value = str(self._qss_builder.normalize_measure(radius) or radius).strip()
        if not radius_value:
            return False
        return self._set_widget_property_if_changed(widget, '_themeBorderRadius', radius_value)

    def _apply_line_edit_padding_theme(self, widget: QWidget, styles: dict[str, Any]) -> bool:
        if not isinstance(widget, QLineEdit):
            return False

        margins = self._style_normalizer.normalize_box_from_mapping(styles, 'padding')
        if margins is None:
            return False

        if widget not in self._styled_line_edit_margin_widgets:
            current = widget.textMargins()
            self._styled_line_edit_margin_widgets[widget] = (
                int(current.left()),
                int(current.top()),
                int(current.right()),
                int(current.bottom()),
            )

        widget.setTextMargins(*margins)
        widget.updateGeometry()
        widget.update()
        return True

    def _apply_runtime_styles(
        self,
        target: str,
        styles: ThemeMap,
        *,
        widgets: list[QWidget] | None = None,
    ) -> None:
        def resolve_part_media_sources(value: Any) -> Any:
            if isinstance(value, dict):
                resolved: dict[str, Any] = {}
                for key, item in cast(dict[str, Any], value).items():
                    if key in {'source', 'path', 'file', 'icon'} and isinstance(item, str) and item.strip():
                        resolved[key] = self._qss_builder.resolve_media_source(item)
                    else:
                        resolved[key] = resolve_part_media_sources(item)
                return resolved
            if isinstance(value, list):
                return [resolve_part_media_sources(item) for item in cast(list[Any], value)]
            return deepcopy(value)

        box_theme: ThemeMap | None = None
        for key in ('background', 'border'):
            if (value := theme_map(styles.get(key))) is not None:
                if box_theme is None:
                    box_theme = {}
                box_theme[key] = deepcopy(value)

        parts_theme = theme_map(styles.get('parts'))
        resolved_parts_theme = (
            cast(ThemeMap, resolve_part_media_sources(parts_theme))
            if parts_theme is not None else
            None
        )

        media_theme = theme_map(styles.get('media'))
        dropdown_theme = theme_map(styles.get('dropdown'))
        items_theme = theme_map(styles.get('items'))
        resolved_media_theme: ThemeMap | None = None
        if media_theme is not None:
            resolved_media_theme = deepcopy(media_theme)
            source = resolved_media_theme.get('source')
            if (not isinstance(source, str) or not source.strip()) and (icon_data := theme_map(resolved_media_theme.get('icon'))) is not None:
                icon_source = icon_data.get('source')
                if isinstance(icon_source, str) and icon_source.strip():
                    source = icon_source
            if isinstance(source, str) and source.strip():
                resolved_media_theme['source'] = self._qss_builder.resolve_media_source(source)

        if normalize_qss_target(target) == '*':
            resolved_media_theme = None
            dropdown_theme = None
            items_theme = None

        if (
            box_theme is None and
            resolved_parts_theme is None and
            resolved_media_theme is None and
            dropdown_theme is None and
            items_theme is None
        ):
            return

        resolved_widgets = widgets if widgets is not None else resolve_target_widgets(self._root, target, include_window=True)
        for widget in resolved_widgets:
            if box_theme is not None and self._uses_painted_box_theme(widget):
                cast(BoxThemeMixin, widget).apply_box_theme(box_theme)
                self._styled_box_widgets.add(widget)

            if resolved_parts_theme is not None and isinstance(widget, self._PARTS_THEME_WIDGET_TYPES):
                widget.apply_theme(resolved_parts_theme)
                self._styled_parts_widgets.add(widget)

            if resolved_media_theme is not None:
                if isinstance(widget, MTMediaWidget):
                    widget.apply_media_theme(resolved_media_theme)
                    self._styled_media_widgets.add(widget)
                    self._clear_widget_media_overlay(widget)
                else:
                    source = resolved_media_theme.get('source')
                    if not isinstance(source, str) or not source.strip():
                        self._clear_widget_media_overlay(widget)
                    else:
                        overlay = self._ensure_media_overlay(widget)
                        overlay.apply_theme(resolved_media_theme)
                        overlay.sync_geometry()
                        overlay.lower()

            if isinstance(widget, MTComboBox):
                if dropdown_theme is not None:
                    try:
                        widget.apply_dropdown_theme(dropdown_theme)
                        self._styled_combo_popup_widgets.add(widget)
                    except RuntimeError:
                        pass
                if items_theme is not None:
                    try:
                        widget.apply_items_theme(items_theme)
                        self._styled_combo_popup_widgets.add(widget)
                    except RuntimeError:
                        pass

    def _ensure_media_overlay(self, widget: QWidget) -> ThemeMediaOverlay:
        if (overlay := self._media_overlays.get(widget)) is not None:
            return overlay

        overlay = ThemeMediaOverlay(widget)
        self._media_overlays[widget] = overlay

        if widget not in self._media_overlay_filters:
            widget.installEventFilter(self)
            self._media_overlay_filters.add(widget)

        return overlay

    def _clear_widget_media_overlay(self, widget: QWidget) -> None:
        if (overlay := self._media_overlays.pop(widget, None)) is not None:
            try:
                overlay.reset_theme()
                overlay.deleteLater()
            except RuntimeError:
                pass

        if widget in self._media_overlay_filters:
            try:
                widget.removeEventFilter(self)
            except RuntimeError:
                pass
            self._media_overlay_filters.discard(widget)

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
        styles = self._qss_styles_for_widgets(styles, widgets or [])
        return self._qss_builder.build(
            obj_name,
            styles,
            selector,
            widgets=widgets,
            root_widget=self._root,
        )

    def _qss_styles_for_widgets(self, styles: ThemeMap, widgets: list[QWidget]) -> ThemeMap:
        if not widgets:
            return styles

        if not all(self._uses_painted_box_theme(widget) for widget in widgets):
            return styles

        if theme_map(styles.get('background')) is None and theme_map(styles.get('border')) is None:
            return styles

        filtered = dict(styles)
        filtered.pop('background', None)
        filtered.pop('border', None)
        return filtered

    def _uses_painted_box_theme(self, widget: QWidget) -> bool:
        if not isinstance(widget, BoxThemeMixin):
            return False
        return bool(widget.PAINTED_BOX_THEME)

    def _apply_layout_theme(self, widget: QWidget, data: ThemeMap) -> bool:
        spacing = self._style_normalizer.normalize_int(data.get('spacing'))
        alignment = self._style_normalizer.normalize_alignment(data.get('align', data.get('alignment')))
        justify = self._style_normalizer.normalize_layout_justify(data.get('justify'))

        layout = widget.layout()
        current_margins = None
        if isinstance(layout, QLayout):
            current = layout.contentsMargins()
            current_margins = (current.left(), current.top(), current.right(), current.bottom())
        else:
            current_margins = widget.property('_themePaddingBox')
            current_margin_tuple = cast(tuple[object, ...] | None, current_margins if isinstance(current_margins, tuple) else None)
            if current_margin_tuple is None or len(current_margin_tuple) != 4:
                current_margins = None
            else:
                current_margins = cast(tuple[int, int, int, int], current_margin_tuple)

        margins = self._normalize_box_from_cascade(data, 'margin', current=current_margins)
        if margins is None and spacing is None and alignment is None and justify is None:
            return False

        if not isinstance(layout, QLayout):
            if margins is None:
                return False
            changed = self._set_widget_property_if_changed(widget, '_themePaddingBox', margins)
            if changed:
                widget.update()
            return changed

        self._remember_layout_defaults(widget, layout)
        original = self._styled_layout_widgets[widget]
        self._clear_layout_justify(layout, original)
        changed = False
        if margins is not None:
            changed = self._set_layout_margins_if_changed(layout, margins) or changed
        if spacing is not None:
            if layout.spacing() != spacing:
                layout.setSpacing(spacing)
                changed = True
        if alignment is not None:
            changed = self._set_layout_alignment_if_changed(layout, alignment) or changed
        if justify is not None:
            self._apply_layout_justify(layout, original, justify)
            changed = True
        return changed

    def _normalize_box_from_cascade(
        self,
        data: dict[str, Any],
        key: str,
        *,
        current: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int, int, int] | None:
        base_source = data.get(key, data.get(f'{key}s'))
        base = self._style_normalizer.normalize_box(base_source)
        sides = {
            side: self._style_normalizer.normalize_int(
                data.get(f'{key}-{side}', data.get(f'{key}_{side}'))
            )
            for side in ('top', 'right', 'bottom', 'left')
        }

        if all(value is None for value in sides.values()):
            return base

        left, top, right, bottom = base or current or (0, 0, 0, 0)
        return (
            sides['left'] if sides['left'] is not None else left,
            sides['top'] if sides['top'] is not None else top,
            sides['right'] if sides['right'] is not None else right,
            sides['bottom'] if sides['bottom'] is not None else bottom,
        )

    def _remember_layout_defaults(self, widget: QWidget, layout: QLayout) -> None:
        if widget in self._styled_layout_widgets:
            return

        margins = layout.contentsMargins()
        self._styled_layout_widgets[widget] = {
            'margin': (
                margins.left(),
                margins.top(),
                margins.right(),
                margins.bottom(),
            ),
            'spacing': int(layout.spacing()),
            'alignment': int(layout.alignment()),
            'justify_indices': [],
        }

    def _apply_viewport_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(widget, QScrollArea):
            return False

        if widget not in self._styled_viewport_margin_widgets:
            current = widget.viewportMargins()
            self._styled_viewport_margin_widgets[widget] = (
                current.left(),
                current.top(),
                current.right(),
                current.bottom(),
            )

        current_viewport_margins = widget.viewportMargins()
        margins = self._normalize_box_from_cascade(
            data,
            'margin',
            current=(
                current_viewport_margins.left(),
                current_viewport_margins.top(),
                current_viewport_margins.right(),
                current_viewport_margins.bottom(),
            ),
        )
        if margins is None:
            return False

        if not self._set_viewport_margins_if_changed(widget, margins):
            return False
        widget.viewport().update()
        widget.updateGeometry()
        return True

    def _apply_geometry_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        min_w = self._style_normalizer.normalize_int(data.get('min_width', data.get('minWidth')))
        max_w = self._style_normalizer.normalize_int(data.get('max_width', data.get('maxWidth')))
        fix_w = self._style_normalizer.normalize_int(data.get('fixed_width', data.get('width')))
        min_h = self._style_normalizer.normalize_int(data.get('min_height', data.get('minHeight')))
        max_h = self._style_normalizer.normalize_int(data.get('max_height', data.get('maxHeight')))
        fix_h = self._style_normalizer.normalize_int(data.get('fixed_height', data.get('height')))

        if all((v is None for v in [min_w, max_w, fix_w, min_h, max_h, fix_h])):
            return False

        if widget not in self._styled_geometry_widgets:
            self._styled_geometry_widgets[widget] = {
                'minimum_width': int(widget.minimumWidth()),
                'maximum_width': int(widget.maximumWidth()),
                'minimum_height': int(widget.minimumHeight()),
                'maximum_height': int(widget.maximumHeight()),
            }

        if fix_w is not None:
            widget.setMinimumWidth(fix_w)
            widget.setMaximumWidth(fix_w)
        else:
            if min_w is not None:
                widget.setMinimumWidth(min_w)
            if max_w is not None:
                widget.setMaximumWidth(max_w)

        if fix_h is not None:
            widget.setMinimumHeight(fix_h)
            widget.setMaximumHeight(fix_h)
        else:
            if min_h is not None:
                widget.setMinimumHeight(min_h)
            if max_h is not None:
                widget.setMaximumHeight(max_h)

        return True

    def _apply_size_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        policy_data = data.get('policy')
        policy = theme_map(policy_data)
        if policy is None:
            return False

        horizontal = self._normalize_size_policy(policy.get('h'))
        vertical = self._normalize_size_policy(policy.get('v'))
        if horizontal is None and vertical is None:
            return False

        current = widget.sizePolicy()
        if widget not in self._styled_size_policy_widgets:
            self._styled_size_policy_widgets[widget] = (
                current.horizontalPolicy(),
                current.verticalPolicy(),
            )

        changed = False
        if horizontal is not None and current.horizontalPolicy() != horizontal:
            current.setHorizontalPolicy(horizontal)
            changed = True
        if vertical is not None and current.verticalPolicy() != vertical:
            current.setVerticalPolicy(vertical)
            changed = True
        if not changed:
            return False

        widget.setSizePolicy(current)
        self._relax_parent_item_alignment_for_policy(widget, horizontal, vertical)
        widget.updateGeometry()
        return True

    def _relax_parent_item_alignment_for_policy(
        self,
        widget: QWidget,
        horizontal: QSizePolicy.Policy | None,
        vertical: QSizePolicy.Policy | None,
    ) -> None:
        parent = widget.parentWidget()
        layout = parent.layout() if isinstance(parent, QWidget) else None
        if not isinstance(layout, QLayout):
            return

        item = None
        for index in range(layout.count()):
            current_item = layout.itemAt(index)
            if current_item is not None and current_item.widget() is widget:
                item = current_item
                break
        if item is None:
            return

        current_alignment = item.alignment()
        if widget not in self._styled_layout_item_alignment_widgets:
            self._styled_layout_item_alignment_widgets[widget] = current_alignment

        relaxed = current_alignment
        if self._is_stretch_policy(horizontal):
            relaxed &= ~(
                Qt.AlignmentFlag.AlignLeft |
                Qt.AlignmentFlag.AlignRight |
                Qt.AlignmentFlag.AlignHCenter
            )
        if self._is_stretch_policy(vertical):
            relaxed &= ~(
                Qt.AlignmentFlag.AlignTop |
                Qt.AlignmentFlag.AlignBottom |
                Qt.AlignmentFlag.AlignVCenter
            )

        if relaxed != current_alignment:
            layout.setAlignment(widget, relaxed)

    def _is_stretch_policy(self, policy: QSizePolicy.Policy | None) -> bool:
        return policy in {
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Ignored,
        }

    def _normalize_size_policy(self, value: Any) -> QSizePolicy.Policy | None:
        if value is None:
            return None

        if isinstance(value, QSizePolicy.Policy):
            return value

        if isinstance(value, int):
            try:
                return QSizePolicy.Policy(value)
            except (TypeError, ValueError):
                return None

        key = str(value).strip().lower().replace('-', '_').replace(' ', '_')
        aliases = {
            'fixed': QSizePolicy.Policy.Fixed,
            'min': QSizePolicy.Policy.Minimum,
            'minimum': QSizePolicy.Policy.Minimum,
            'max': QSizePolicy.Policy.Maximum,
            'maximum': QSizePolicy.Policy.Maximum,
            'preferred': QSizePolicy.Policy.Preferred,
            'pref': QSizePolicy.Policy.Preferred,
            'content': QSizePolicy.Policy.Preferred,
            'auto': QSizePolicy.Policy.Preferred,
            'expanding': QSizePolicy.Policy.Expanding,
            'expand': QSizePolicy.Policy.Expanding,
            'stretch': QSizePolicy.Policy.Expanding,
            'fill': QSizePolicy.Policy.Expanding,
            'min_expanding': QSizePolicy.Policy.MinimumExpanding,
            'minimum_expanding': QSizePolicy.Policy.MinimumExpanding,
            'ignored': QSizePolicy.Policy.Ignored,
            'ignore': QSizePolicy.Policy.Ignored,
        }
        return aliases.get(key)

    def _apply_text_alignment_theme(
        self,
        widget: QWidget,
        data: dict[str, Any],
        *,
        align_keys: tuple[str, ...] = ('align', 'alignment'),
    ) -> bool:
        if not isinstance(widget, self._ALIGNED_WIDGET_TYPES):
            return False

        alignment = None
        for key in align_keys:
            if (alignment := self._style_normalizer.normalize_alignment(data.get(key))) is not None:
                break
        if alignment is None:
            return False

        if widget not in self._styled_text_alignment_widgets:
            try:
                current_value = widget.alignment()
                if widget not in self._styled_text_alignment_widgets:
                    self._styled_text_alignment_widgets[widget] = coerce_int(
                        current_value,
                        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    ) or int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if current_value == alignment:
                    return False
            except RuntimeError:
                pass

        widget.setAlignment(alignment)
        return True

    def _apply_text_focus_alignment_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(widget, MTLineEdit):
            return False

        align_data = data.get('align', data.get('alignment'))
        align_state_data = theme_map(align_data) or {}
        focused = self._style_normalizer.normalize_alignment(align_state_data.get('focused'))
        unfocused = self._style_normalizer.normalize_alignment(align_state_data.get('unfocused'))
        if focused is None and unfocused is None:
            if (
                ('align' in data or 'alignment' in data) and
                widget in self._styled_text_focus_alignment_widgets
            ):
                widget.clear_focus_alignments()
                self._styled_text_focus_alignment_widgets.discard(widget)
                return True
            return False

        widget.set_focus_alignments(focused=focused, unfocused=unfocused)
        self._styled_text_focus_alignment_widgets.add(widget)
        return True

    def _apply_line_edit_text_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(widget, MTLineEdit):
            return False

        raw_text_color = data.get('color')
        raw_placeholder_color = data.get('placeholder_color', data.get('placeholder-color'))
        if raw_text_color is None and raw_placeholder_color is None:
            return False

        if widget not in self._styled_line_edit_text_widgets:
            self._styled_line_edit_text_widgets[widget] = QPalette(widget.palette())

        widget.set_line_edit_text_theme(
            text_color=to_qcolor(raw_text_color),
            placeholder_color=to_qcolor(raw_placeholder_color),
        )
        return True

    def _apply_text_font_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if 'font' not in data:
            return False

        font_data = data.get('font')
        if font_data is False or font_data is None:
            if widget in self._styled_text_font_widgets:
                font = QFont(self._styled_text_font_widgets[widget])
                if self._set_font_if_changed(widget, font):
                    widget.updateGeometry()
                    widget.update()
                    return True
            return False

        font_config = theme_map(font_data)
        if font_config is None:
            return False

        font = QFont(widget.font())
        changed = False

        family = self._font_family_for_qfont(font_config.get('family'))
        if family:
            font.setFamily(family)
            changed = True

        size_value = font_config.get('size')
        if size_value is not None and not isinstance(size_value, bool):
            if isinstance(size_value, str) and size_value.strip().lower().endswith('pt'):
                point_size = self._style_normalizer.normalize_float(size_value.strip()[:-2])
                if point_size is not None and point_size > 0:
                    font.setPointSizeF(point_size)
                    changed = True
            else:
                pixel_size = self._style_normalizer.normalize_int(size_value)
                if pixel_size is not None and pixel_size > 0:
                    font.setPixelSize(pixel_size)
                    changed = True

        weight_value = font_config.get('weight')
        if weight_value is not None and not isinstance(weight_value, bool):
            if isinstance(weight_value, str):
                key = weight_value.strip().lower()
                weight = {
                    'thin': QFont.Weight.Thin,
                    'extralight': QFont.Weight.ExtraLight,
                    'extra_light': QFont.Weight.ExtraLight,
                    'light': QFont.Weight.Light,
                    'normal': QFont.Weight.Normal,
                    'regular': QFont.Weight.Normal,
                    'medium': QFont.Weight.Medium,
                    'demibold': QFont.Weight.DemiBold,
                    'demi_bold': QFont.Weight.DemiBold,
                    'semibold': QFont.Weight.DemiBold,
                    'semi_bold': QFont.Weight.DemiBold,
                    'bold': QFont.Weight.Bold,
                    'extrabold': QFont.Weight.ExtraBold,
                    'extra_bold': QFont.Weight.ExtraBold,
                    'black': QFont.Weight.Black,
                }.get(key)
                if weight is not None:
                    font.setWeight(weight)
                    changed = True
            else:
                weight = self._style_normalizer.normalize_int(weight_value)
                if weight is not None:
                    font.setWeight(QFont.Weight(max(1, min(1000, weight))))
                    changed = True

        style_value = font_config.get('style')
        if style_value is not None and not isinstance(style_value, bool):
            style = str(style_value).strip().lower()
            if style:
                font.setItalic(style in {'italic', 'oblique'})
                changed = True

        if not changed:
            return False

        if widget not in self._styled_text_font_widgets:
            self._styled_text_font_widgets[widget] = QFont(widget.font())

        if not self._set_font_if_changed(widget, font):
            return False
        widget.updateGeometry()
        widget.update()
        return True

    def _font_family_for_qfont(self, value: Any) -> str:
        if value is None:
            return ''

        resolved = self._qss_builder.resolve_font_family(str(value))
        if not resolved:
            return ''

        family = resolved.strip()
        if ',' in family:
            family = family.split(',', 1)[0].strip()

        if len(family) >= 2 and family[0] == family[-1] and family[0] in {'"', "'"}:
            family = family[1:-1]

        return family.strip()

    def _apply_shadow_effect_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if 'shadow' not in data:
            return False

        shadow = self._style_normalizer.normalize_shadow(data.get('shadow'))
        if shadow is None:
            widget.setGraphicsEffect(cast(Any, None))
            self._styled_effect_widgets.add(widget)
            return True

        effect = QGraphicsDropShadowEffect(widget)
        effect.setColor(shadow['color'])
        effect.setBlurRadius(float(shadow['blur']))
        effect.setOffset(shadow['offset'])
        widget.setGraphicsEffect(effect)
        self._styled_effect_widgets.add(widget)
        return True

    def _apply_button_icon_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if 'icon' not in data or not isinstance(widget, QAbstractButton):
            return False

        if widget not in self._styled_button_icon_widgets:
            self._styled_button_icon_widgets[widget] = (
                QIcon(widget.icon()),
                QSize(widget.iconSize()),
            )

        icon_data = data.get('icon')
        if icon_data is False or icon_data is None:
            icon, icon_size = self._styled_button_icon_widgets[widget]
            widget.setIcon(QIcon(icon))
            widget.setIconSize(QSize(icon_size))
            widget.updateGeometry()
            widget.update()
            return True

        if isinstance(icon_data, str):
            icon_data = {'source': icon_data}
        icon_map = theme_map(icon_data)
        if icon_map is None:
            return False

        source = icon_map.get('source', icon_map.get('path', icon_map.get('file')))
        if not isinstance(source, str) or not source.strip():
            return False

        resolved_source = self._qss_builder.resolve_media_source(source)
        icon = QIcon(resolved_source)
        if icon.isNull():
            return False

        size = self._normalize_icon_size(icon_map)
        if size is None:
            size = QSize(widget.iconSize())
            if not size.isValid() or size.isEmpty():
                size = icon.actualSize(QSize(16, 16))
        if not size.isValid() or size.isEmpty():
            size = QSize(16, 16)

        widget.setIcon(icon)
        widget.setIconSize(size)
        widget.updateGeometry()
        widget.update()
        return True

    def _normalize_icon_size(self, data: dict[str, Any]) -> QSize | None:
        raw_size = data.get('size')
        raw_size_sequence = cast(list[object] | tuple[object, ...] | None, raw_size if isinstance(raw_size, (list, tuple)) else None)
        raw_size_map = theme_map(cast(object, raw_size))
        if raw_size_sequence is not None and len(raw_size_sequence) >= 2:
            width = self._style_normalizer.normalize_int(raw_size_sequence[0])
            height = self._style_normalizer.normalize_int(raw_size_sequence[1])
        elif raw_size_map is not None:
            width = self._style_normalizer.normalize_int(raw_size_map.get('width', raw_size_map.get('w')))
            height = self._style_normalizer.normalize_int(raw_size_map.get('height', raw_size_map.get('h')))
        elif raw_size is not None:
            value = self._style_normalizer.normalize_int(raw_size)
            width = value
            height = value
        else:
            width = self._style_normalizer.normalize_int(data.get('width', data.get('w')))
            height = self._style_normalizer.normalize_int(data.get('height', data.get('h')))

        if width is None and height is None:
            return None
        if width is None:
            width = height
        if height is None:
            height = width
        if width is None or height is None or width <= 0 or height <= 0:
            return None
        return QSize(int(width), int(height))

    def _apply_layout_justify(self, layout: QLayout, original: LayoutSnapshot, justify: str) -> None:
        if not isinstance(layout, QBoxLayout):
            original['justify_indices'] = []
            return

        indices: list[int] = []
        match justify:
            case 'start':
                pass
            case 'end':
                layout.insertStretch(0, 1)
                indices = [0]
            case 'center':
                layout.insertStretch(0, 1)
                layout.addStretch(1)
                indices = [0, layout.count() - 1]
            case 'space_between':
                widget_positions = [
                    index
                    for index in range(layout.count())
                    if (item := layout.itemAt(index)) is not None and item.spacerItem() is None
                ]
                for position in reversed(widget_positions[:-1]):
                    insert_index = position + 1
                    layout.insertStretch(insert_index, 1)
                    indices.append(insert_index)
                indices.sort(reverse=True)
            case _:
                pass
        original['justify_indices'] = indices

    def _clear_layout_justify(self, layout: QLayout, original: LayoutSnapshot) -> None:
        indices = original['justify_indices']
        for index in sorted({int(value) for value in indices}, reverse=True):
            item = layout.takeAt(index)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        original['justify_indices'] = []

    def _normalize_bool_value(self, data: Any) -> bool | None:
        if isinstance(data, bool):
            return data
        if isinstance(data, (int, float)):
            return bool(data)
        if isinstance(data, str):
            value = data.strip().lower()
            if value in {'true', '1', 'yes', 'on', 'enabled', 'enable'}:
                return True
            if value in {'false', '0', 'no', 'off', 'disabled', 'disable', 'none'}:
                return False
        return None
