from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, QSize, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QBoxLayout, QGraphicsDropShadowEffect, QLayout, QScrollArea, QSizePolicy, QWidget

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
from src.theme.storage.io import load_theme_payload


class ThemeManager(QObject):
    theme_changed = Signal(dict, dict)
    
    def __init__(
        self,
        root: QWidget,
        default_theme: dict | None = None,
        *,
        emit_theme_changed: bool = True,
    ):
        super().__init__()
        self._root = root
        self._default_theme = default_theme or {}
        self._current_theme: dict[str, Any] = normalize_theme_payload(self._default_theme)
        self._qss_builder = QssBuilder()
        self._style_normalizer = StyleNormalizer()
        self._styled_parts_widgets: set[QWidget] = set()
        self._styled_media_widgets: set[QWidget] = set()
        self._styled_combo_popup_widgets: set[QWidget] = set()
        self._styled_theme_prop_widgets: set[QWidget] = set()
        self._styled_rainbow_target_widgets: dict[QWidget, Any] = {}
        self._styled_geometry_widgets: dict[QWidget, dict[str, int]] = {}
        self._styled_viewport_margin_widgets: dict[QScrollArea, tuple[int, int, int, int]] = {}
        self._styled_size_policy_widgets: dict[QWidget, tuple[QSizePolicy.Policy, QSizePolicy.Policy]] = {}
        self._styled_layout_item_alignment_widgets: dict[QWidget, Qt.AlignmentFlag] = {}
        self._styled_layout_widgets: dict[QWidget, dict[str, Any]] = {}
        self._styled_text_alignment_widgets: dict[QWidget, int] = {}
        self._styled_effect_widgets: set[QWidget] = set()
        self._styled_text_shadow_widgets: set[QWidget] = set()
        self._styled_text_border_widgets: set[QWidget] = set()
        self._styled_text_icon_widgets: set[QWidget] = set()
        self._styled_text_spacing_widgets: set[QWidget] = set()
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
        self._pending_theme_change: tuple[dict[str, Any], dict[str, Any]] | None = None
        self._last_emitted_theme_change: tuple[dict[str, Any], dict[str, Any]] | None = None
        self._emit_theme_changed_enabled = bool(emit_theme_changed)
        self._qss_builder.font_ready.connect(self._on_async_font_ready)

    def eventFilter(self, obj, event):
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

    def load(self, theme: Path | dict, *, merge_with_default: bool = False):
        if isinstance(theme, Path):
            self._theme_base_dir = theme.parent
            self._qss_builder.set_theme_base_dir(self._theme_base_dir)
            theme = load_theme_payload(theme)
            if theme is None:
                return
        else:
            self._theme_base_dir = None
            self._qss_builder.set_theme_base_dir(None)

        if not isinstance(theme, dict):
            return

        if merge_with_default:
            default_theme = normalize_theme_payload(self._default_theme)
            user_theme = normalize_theme_payload(theme)
            merged_theme = deep_merge_dicts(
                {key: value for key, value in default_theme.items() if key != 'widgets'},
                {key: value for key, value in user_theme.items() if key != 'widgets'},
            )
            merged_widgets: dict[str, dict[str, dict]] = deepcopy(default_theme.get('widgets', {}))
            user_widgets: dict[str, dict[str, dict]] = user_theme.get('widgets', {})

            for obj_name, data in user_widgets.items():
                merged_widgets[obj_name] = merge_widget_theme_data(
                    merged_widgets.get(obj_name),
                    data,
                )

            merged_theme['widgets'] = merged_widgets
            self._current_theme = merged_theme
            return

        self._current_theme = normalize_theme_payload(theme)

    def apply(self):
        self._reset_runtime_styles()
        qss_parts = []
        animations = {}
        runtime_styles_by_widget: dict[QWidget, dict[str, Any]] = {}

        widget_items = list(self._current_theme.get('widgets', {}).items())
        for _index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            if not isinstance(styles, dict):
                continue

            qss_target = normalize_qss_target(target)
            effective_styles = styles
            if qss_target == '*' and isinstance(styles.get('media'), dict):
                effective_styles = {key: value for key, value in styles.items() if key != 'media'}

            widgets = resolve_target_widgets(self._root, target, include_window=True)
            style_options, effective_styles = self._extract_style_options(effective_styles)
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

            selector = '' if qss_target.startswith(('*', 'MT')) else '#'
            qss_styles = self._strip_checkable_state_styles(effective_styles)
            if (qss := self._build_qss(qss_target, qss_styles, selector, widgets=widgets)):
                qss_parts.append(qss)
            anims = effective_styles.get('animations')
            if not anims and isinstance(styles.get('animations'), (dict, list)):
                anims = styles.get('animations')
            if anims:
                animations[target] = deepcopy(anims)

        self._root.setStyleSheet('\n'.join(qss_parts))
        self._emit_theme_changed(animations, deepcopy(self._current_theme.get('widgets', {})))

    def apply_to_subtree(self, root: QWidget) -> None:
        if not isinstance(root, QWidget):
            return

        qss_parts: list[str] = []
        runtime_styles_by_widget: dict[QWidget, dict[str, Any]] = {}
        widget_items = list(self._current_theme.get('widgets', {}).items())

        for _index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            if not isinstance(styles, dict):
                continue

            qss_target = normalize_qss_target(target)
            effective_styles = styles
            if qss_target == '*' and isinstance(styles.get('media'), dict):
                effective_styles = {
                    key: value for key, value in styles.items() if key != 'media'
                }

            widgets = resolve_target_widgets(root, target, include_window=False)
            if not widgets:
                continue

            style_options, effective_styles = self._extract_style_options(effective_styles)
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

            selector = '' if qss_target.startswith(('*', 'MT')) else '#'
            qss_styles = self._strip_checkable_state_styles(effective_styles)
            if qss := self._build_qss(
                qss_target,
                qss_styles,
                selector,
                widgets=widgets,
            ):
                qss_parts.append(qss)

        root.setStyleSheet('\n'.join(qss_parts))
        root.update()

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

    def _emit_theme_changed(self, animations: dict[str, Any], theme_widgets: dict[str, Any]) -> None:
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

    def _reset_runtime_styles(self) -> None:
        for widget, original in self._styled_rainbow_target_widgets.items():
            try:
                widget.setProperty('rainbowBorderTarget', original)
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
                margin = original.get('margin')
                if isinstance(margin, tuple) and len(margin) == 4:
                    layout.setContentsMargins(*margin)
                if isinstance((spacing := original.get('spacing')), int):
                    layout.setSpacing(spacing)
                if isinstance((alignment := original.get('alignment')), int):
                    layout.setAlignment(Qt.AlignmentFlag(alignment))
            except RuntimeError:
                continue

        for widget, original_alignment in self._styled_text_alignment_widgets.items():
            try:
                set_alignment = getattr(widget, 'setAlignment', None)
                if callable(set_alignment):
                    set_alignment(Qt.AlignmentFlag(int(original_alignment)))
            except RuntimeError:
                continue

        for widget, original_font in self._styled_text_font_widgets.items():
            try:
                widget.setFont(QFont(original_font))
                widget.updateGeometry()
                widget.update()
            except RuntimeError:
                continue

        for widget in self._styled_text_shadow_widgets:
            try:
                clear_text_shadow = getattr(widget, 'clear_text_shadow', None)
                if callable(clear_text_shadow):
                    clear_text_shadow()
            except RuntimeError:
                continue

        for widget in self._styled_text_border_widgets:
            try:
                clear_text_border = getattr(widget, 'clear_text_border', None)
                if callable(clear_text_border):
                    clear_text_border()
            except RuntimeError:
                continue

        for widget in self._styled_text_icon_widgets:
            try:
                restore_default_text_icon_state = getattr(widget, 'restore_default_text_icon_state', None)
                clear_text_icon = getattr(widget, 'clear_text_icon', None)
                if callable(restore_default_text_icon_state):
                    restore_default_text_icon_state()
                elif callable(clear_text_icon):
                    clear_text_icon()
            except RuntimeError:
                continue

        for widget in self._styled_text_spacing_widgets:
            try:
                clear_text_spacing = getattr(widget, 'clear_text_spacing', None)
                if callable(clear_text_spacing):
                    clear_text_spacing()
            except RuntimeError:
                continue

        for widget in self._styled_text_focus_alignment_widgets:
            try:
                clear_focus_alignments = getattr(widget, 'clear_focus_alignments', None)
                if callable(clear_focus_alignments):
                    clear_focus_alignments()
            except RuntimeError:
                continue

        for widget, margins in self._styled_line_edit_margin_widgets.items():
            try:
                set_text_margins = getattr(widget, 'setTextMargins', None)
                if callable(set_text_margins):
                    set_text_margins(*margins)
                    widget.updateGeometry()
                    widget.update()
            except RuntimeError:
                continue

        for widget, original_palette in self._styled_line_edit_text_widgets.items():
            try:
                widget.setPalette(QPalette(original_palette))
                clear_line_edit_text_theme = getattr(widget, 'clear_line_edit_text_theme', None)
                if callable(clear_line_edit_text_theme):
                    clear_line_edit_text_theme()
                widget.update()
            except RuntimeError:
                continue

        for widget in self._styled_box_widgets:
            try:
                clear_box_theme = getattr(widget, 'clear_box_theme', None)
                if callable(clear_box_theme):
                    clear_box_theme()
            except RuntimeError:
                continue

        for widget in self._styled_effect_widgets:
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                continue

        for widget in self._styled_parts_widgets:
            try:
                reset_theme = getattr(widget, 'reset_theme', None)
                if callable(reset_theme):
                    reset_theme()
            except RuntimeError:
                continue

        for widget in self._styled_media_widgets:
            try:
                reset_theme = getattr(widget, 'reset_theme', None)
                if callable(reset_theme):
                    reset_theme()
            except RuntimeError:
                continue

        for widget in self._styled_combo_popup_widgets:
            try:
                reset_theme = getattr(widget, 'reset_theme', None)
                if callable(reset_theme):
                    reset_theme()
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
        self._styled_rainbow_target_widgets.clear()
        self._styled_geometry_widgets.clear()
        self._styled_viewport_margin_widgets.clear()
        self._styled_size_policy_widgets.clear()
        self._styled_layout_item_alignment_widgets.clear()
        self._styled_layout_widgets.clear()
        self._styled_text_alignment_widgets.clear()
        self._styled_effect_widgets.clear()
        self._styled_text_shadow_widgets.clear()
        self._styled_text_border_widgets.clear()
        self._styled_text_icon_widgets.clear()
        self._styled_text_spacing_widgets.clear()
        self._styled_text_focus_alignment_widgets.clear()
        self._styled_line_edit_margin_widgets.clear()
        self._styled_line_edit_text_widgets.clear()
        self._styled_text_font_widgets.clear()
        self._styled_box_widgets.clear()
        self._media_overlays.clear()
        self._media_overlay_filters.clear()

    def _has_checkable_state_styles(self, styles: dict[str, Any]) -> bool:
        return isinstance(styles, dict) and (
            isinstance(styles.get('checked'), dict) or
            isinstance(styles.get('unchecked'), dict)
        )

    def _strip_checkable_state_styles(self, styles: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(styles, dict):
            return {}
        return {
            key: deepcopy(value)
            for key, value in styles.items()
            if key not in {'checked', 'unchecked'}
        }

    def _merge_checkable_state_styles(self, widget: QWidget, styles: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(styles, dict):
            return {}

        merged = self._strip_checkable_state_styles(styles)
        state_styles = styles.get('checked') if self._widget_is_checked(widget) else styles.get('unchecked')
        if isinstance(state_styles, dict):
            merged = merge_widget_theme_data(merged, state_styles)
        return merged

    def _widget_is_checked(self, widget: QWidget) -> bool:
        is_checkable = getattr(widget, 'isCheckable', None)
        is_checked = getattr(widget, 'isChecked', None)
        if not callable(is_checkable) or not callable(is_checked):
            return False
        try:
            return bool(is_checkable() and is_checked())
        except RuntimeError:
            return False

    def _bind_checkable_state_style(self, widget: QWidget) -> None:
        if widget in self._checkable_state_style_slots:
            return

        toggled = getattr(widget, 'toggled', None)
        if toggled is None:
            return

        self._checkable_state_style_base_qss.setdefault(widget, widget.styleSheet())
        slot = lambda _checked, w=widget, self=self: QTimer.singleShot(0, lambda: self._refresh_checkable_state_widget(w))
        self._checkable_state_style_slots[widget] = slot
        toggled.connect(slot)

    def _refresh_checkable_state_widget(self, widget: QWidget) -> None:
        if not isinstance(widget, QWidget):
            return

        try:
            widget.objectName()
        except RuntimeError:
            return

        merged_styles: dict[str, Any] = {}
        widget_items = list(self._current_theme.get('widgets', {}).items())
        for _index, (target, styles) in sorted(
            enumerate(widget_items),
            key=self._theme_widget_sort_key,
        ):
            if not isinstance(styles, dict):
                continue

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

    def _extract_style_options(self, styles: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(styles, dict):
            return {}, {}

        options: dict[str, Any] = {}
        filtered = dict(styles)
        if 'clear' in filtered:
            options['clear'] = bool(filtered.pop('clear'))
        return options, filtered

    def _clear_target_widget_styles(self, widgets: list[QWidget]) -> None:
        for widget in widgets:
            try:
                widget.setStyleSheet('')
                clear_box_theme = getattr(widget, 'clear_box_theme', None)
                if callable(clear_box_theme):
                    clear_box_theme()
                widget.update()
            except RuntimeError:
                continue

    def _apply_theme_helper_properties(self, styles: dict[str, dict], widgets: list[QWidget]) -> None:
        if not isinstance(styles, dict):
            return

        needs_relative_resolution = self._qss_builder.contains_percent_radius(styles)
        for widget in widgets:
            raw_padding_box = self._style_normalizer.normalize_box_from_mapping(styles, 'padding')
            if raw_padding_box is not None:
                widget.setProperty('_themePaddingBox', raw_padding_box)

            resolved_styles = self._qss_builder.resolve_relative_styles(styles, widget) if needs_relative_resolution else styles
            applied = False

            if 'rainbow' in resolved_styles:
                rainbow_target = self._normalize_bool_value(resolved_styles.get('rainbow'))
                if rainbow_target is not None and widget.property('rainbowBorderExcluded') is not True:
                    if widget not in self._styled_rainbow_target_widgets:
                        self._styled_rainbow_target_widgets[widget] = widget.property('rainbowBorderTarget')
                    widget.setProperty('rainbowBorderTarget', rainbow_target)
                    applied = True

            if isinstance((bg_data := resolved_styles.get('background')), dict):
                if (bg_rule := self._qss_builder.build_background_color(bg_data.get('color'))):
                    widget.setProperty('_themeBackgroundRule', bg_rule)
                    applied = True
                if not isinstance(resolved_styles.get('border'), dict):
                    radius = bg_data.get('radius')
                    if radius is not None:
                        radius_value = str(self._qss_builder.normalize_measure(radius) or radius).strip()
                        if radius_value:
                            widget.setProperty('_themeBorderRadius', radius_value)
                            applied = True

            if isinstance((border_data := resolved_styles.get('border')), dict):
                if (border_rule := self._qss_builder.build_border(border_data)):
                    widget.setProperty('_themeBorderRule', border_rule)
                    applied = True
                background_data = resolved_styles.get('background') if isinstance(resolved_styles.get('background'), dict) else {}
                radius = border_data.get('radius', background_data.get('radius') if isinstance(background_data, dict) else None)
                if radius is not None:
                    radius_value = str(self._qss_builder.normalize_measure(radius) or radius).strip()
                    if radius_value:
                        widget.setProperty('_themeBorderRadius', radius_value)
                        applied = True

            if (padding_rule := self._qss_builder.build_padding_rule(resolved_styles)):
                widget.setProperty('_themePaddingRule', padding_rule)
                widget.setProperty('_themePaddingBox', self._style_normalizer.normalize_box_from_mapping(resolved_styles, 'padding'))
                applied = True

            if self._apply_line_edit_padding_theme(widget, resolved_styles):
                applied = True

            if isinstance((text_data := resolved_styles.get('text')), dict):
                if self._apply_text_font_theme(widget, text_data):
                    applied = True
                if self._apply_text_alignment_theme(widget, text_data, align_keys=('align', 'alignment')):
                    applied = True
                if self._apply_text_focus_alignment_theme(widget, text_data):
                    applied = True
                if self._apply_line_edit_text_theme(widget, text_data):
                    applied = True
                if self._apply_text_shadow_theme(widget, text_data):
                    applied = True
                if self._apply_text_border_theme(widget, text_data):
                    applied = True
                if self._apply_text_icon_theme(widget, text_data):
                    applied = True
                if self._apply_text_spacing_theme(widget, text_data):
                    applied = True

            if self._apply_text_icon_theme(widget, resolved_styles):
                applied = True

            if isinstance((effects_data := resolved_styles.get('effects')), dict):
                if self._apply_shadow_effect_theme(widget, effects_data):
                    applied = True

            if isinstance((layout_data := resolved_styles.get('layout')), dict):
                if self._apply_layout_theme(widget, layout_data):
                    applied = True

            if isinstance((viewport_data := resolved_styles.get('viewport')), dict):
                if self._apply_viewport_theme(widget, viewport_data):
                    applied = True

            if isinstance((size_data := resolved_styles.get('size')), dict):
                if self._apply_size_theme(widget, size_data):
                    applied = True

            if isinstance((geometry_data := resolved_styles.get('geometry')), dict):
                if self._apply_geometry_theme(widget, geometry_data):
                    applied = True

            if applied:
                self._styled_theme_prop_widgets.add(widget)

    def _apply_line_edit_padding_theme(self, widget: QWidget, styles: dict[str, Any]) -> bool:
        if not isinstance(styles, dict):
            return False

        set_text_margins = getattr(widget, 'setTextMargins', None)
        text_margins = getattr(widget, 'textMargins', None)
        if not callable(set_text_margins) or not callable(text_margins):
            return False

        margins = self._style_normalizer.normalize_box_from_mapping(styles, 'padding')
        if margins is None:
            return False

        if widget not in self._styled_line_edit_margin_widgets:
            current = text_margins()
            self._styled_line_edit_margin_widgets[widget] = (
                int(current.left()),
                int(current.top()),
                int(current.right()),
                int(current.bottom()),
            )

        set_text_margins(*margins)
        widget.updateGeometry()
        widget.update()
        return True

    def _apply_runtime_styles(
        self,
        target: str,
        styles: dict[str, dict],
        *,
        widgets: list[QWidget] | None = None,
    ) -> None:
        if not isinstance(styles, dict):
            return

        parts_theme = styles.get('parts')
        media_theme = styles.get('media')
        dropdown_theme = styles.get('dropdown')
        items_theme = styles.get('items')
        box_theme = self._extract_box_theme(styles)
        if normalize_qss_target(target) == '*':
            media_theme = None
            dropdown_theme = None
            items_theme = None
        if (
            not isinstance(parts_theme, dict) and
            not isinstance(media_theme, dict) and
            not isinstance(dropdown_theme, dict) and
            not isinstance(items_theme, dict) and
            not isinstance(box_theme, dict)
        ):
            return

        resolved_media_theme = self._resolve_media_theme(media_theme) if isinstance(media_theme, dict) else None
        resolved_widgets = widgets if widgets is not None else resolve_target_widgets(self._root, target, include_window=True)
        for widget in resolved_widgets:
            if isinstance(box_theme, dict):
                if self._uses_painted_box_theme(widget) and (apply_box_theme := getattr(widget, 'apply_box_theme', None)) and callable(apply_box_theme):
                    apply_box_theme(box_theme)
                    self._styled_box_widgets.add(widget)
            if isinstance(parts_theme, dict):
                if (apply_theme := getattr(widget, 'apply_theme', None)) and callable(apply_theme):
                    apply_theme(self._resolve_parts_media_sources(parts_theme))
                    self._styled_parts_widgets.add(widget)
            if isinstance(resolved_media_theme, dict):
                if (apply_media_theme := getattr(widget, 'apply_media_theme', None)) and callable(apply_media_theme):
                    apply_media_theme(resolved_media_theme)
                    self._styled_media_widgets.add(widget)
                    self._clear_widget_media_overlay(widget)
                else:
                    self._apply_widget_media_overlay(widget, resolved_media_theme)
            if isinstance(dropdown_theme, dict):
                self._apply_combo_popup_theme(widget, dropdown_theme)
            if isinstance(items_theme, dict):
                self._apply_combo_items_theme(widget, items_theme)

    def _resolve_parts_media_sources(self, data: dict[str, Any]) -> dict[str, Any]:
        def resolve(value: Any) -> Any:
            if isinstance(value, dict):
                resolved_dict: dict[str, Any] = {}
                for key, item in value.items():
                    if key in {'source', 'path', 'file', 'icon'} and isinstance(item, str) and item.strip():
                        resolved_dict[key] = self._qss_builder.resolve_media_source(item)
                    else:
                        resolved_dict[key] = resolve(item)
                return resolved_dict
            if isinstance(value, list):
                return [resolve(item) for item in value]
            return deepcopy(value)

        return resolve(data)

    def _extract_box_theme(self, styles: dict[str, Any]) -> dict[str, Any] | None:
        box_theme: dict[str, Any] = {}
        for key in ('background', 'border'):
            value = styles.get(key)
            if isinstance(value, dict):
                box_theme[key] = deepcopy(value)
        return box_theme or None

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

    def _apply_widget_media_overlay(self, widget: QWidget, media_theme: dict[str, Any]) -> None:
        if not isinstance(media_theme, dict):
            self._clear_widget_media_overlay(widget)
            return

        source = media_theme.get('source')
        if not isinstance(source, str) or not source.strip():
            self._clear_widget_media_overlay(widget)
            return

        overlay = self._ensure_media_overlay(widget)
        overlay.apply_theme(media_theme)
        overlay.sync_geometry()
        overlay.lower()

    def _resolve_media_theme(self, data: dict[str, Any]) -> dict[str, Any]:
        resolved = deepcopy(data)

        source = resolved.get('source')
        if not isinstance(source, str) or not source.strip():
            icon_data = resolved.get('icon')
            if isinstance(icon_data, dict):
                icon_source = icon_data.get('source')
                if isinstance(icon_source, str) and icon_source.strip():
                    source = icon_source

        if isinstance(source, str) and source.strip():
            resolved['source'] = self._qss_builder.resolve_media_source(source)
        return resolved

    def _apply_combo_popup_theme(self, widget: QWidget, dropdown_theme: dict[str, Any]) -> None:
        if not isinstance(dropdown_theme, dict):
            return

        try:
            apply_dropdown_theme = getattr(widget, 'apply_dropdown_theme', None)
            if not callable(apply_dropdown_theme):
                return
            apply_dropdown_theme(dropdown_theme)
            self._styled_combo_popup_widgets.add(widget)
        except RuntimeError:
            return

    def _apply_combo_items_theme(self, widget: QWidget, items_theme: dict[str, Any]) -> None:
        if not isinstance(items_theme, dict):
            return

        try:
            apply_items_theme = getattr(widget, 'apply_items_theme', None)
            if not callable(apply_items_theme):
                return
            apply_items_theme(items_theme)
            self._styled_combo_popup_widgets.add(widget)
        except RuntimeError:
            return

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
        if isinstance(base_target, str) and base_target.startswith('MT'):
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

    def _target_specificity(self, target: str, properties: list[str]) -> int:
        text = str(target or '')
        wildcard_count = text.count('*') + text.count('?')
        literal_length = len(text.replace('*', '').replace('?', ''))
        return (len(properties) * 10000) + literal_length - (wildcard_count * 1000)

    def _build_qss(
        self,
        obj_name: str,
        styles: dict[str, dict],
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

    def _qss_styles_for_widgets(self, styles: dict[str, Any], widgets: list[QWidget]) -> dict[str, Any]:
        if not isinstance(styles, dict) or not widgets:
            return styles

        if not all(self._uses_painted_box_theme(widget) for widget in widgets):
            return styles

        if not isinstance(styles.get('background'), dict) and not isinstance(styles.get('border'), dict):
            return styles

        filtered = dict(styles)
        filtered.pop('background', None)
        filtered.pop('border', None)
        return filtered

    def _uses_painted_box_theme(self, widget: QWidget) -> bool:
        if not callable(getattr(widget, 'apply_box_theme', None)):
            return False
        return bool(getattr(widget, 'PAINTED_BOX_THEME', True))

    def _apply_layout_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False

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
            if not isinstance(current_margins, tuple) or len(current_margins) != 4:
                current_margins = None

        margins = self._normalize_box_from_cascade(data, 'margin', current=current_margins)
        if margins is None and spacing is None and alignment is None and justify is None:
            return False

        if not isinstance(layout, QLayout):
            if margins is None:
                return False
            widget.setProperty('_themePaddingBox', margins)
            widget.update()
            return True

        self._remember_layout_defaults(widget, layout)
        original = self._styled_layout_widgets.get(widget, {})
        self._clear_layout_justify(layout, original)
        if margins is not None:
            layout.setContentsMargins(*margins)
        if spacing is not None:
            layout.setSpacing(spacing)
        if alignment is not None:
            layout.setAlignment(alignment)
        if justify is not None:
            self._apply_layout_justify(layout, original, justify)
        return True

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
        if not isinstance(widget, QScrollArea) or not isinstance(data, dict):
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

        widget.setViewportMargins(*margins)
        widget.viewport().update()
        widget.updateGeometry()
        return True

    def _apply_geometry_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False

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
        if not isinstance(data, dict):
            return False

        policy_data = data.get('policy')
        if not isinstance(policy_data, dict):
            return False

        horizontal = self._normalize_size_policy(policy_data.get('h'))
        vertical = self._normalize_size_policy(policy_data.get('v'))
        if horizontal is None and vertical is None:
            return False

        current = widget.sizePolicy()
        if widget not in self._styled_size_policy_widgets:
            self._styled_size_policy_widgets[widget] = (
                current.horizontalPolicy(),
                current.verticalPolicy(),
            )

        if horizontal is not None:
            current.setHorizontalPolicy(horizontal)
        if vertical is not None:
            current.setVerticalPolicy(vertical)
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
        if not isinstance(data, dict):
            return False

        set_alignment = getattr(widget, 'setAlignment', None)
        if not callable(set_alignment):
            return False

        alignment = None
        for key in align_keys:
            if (alignment := self._style_normalizer.normalize_alignment(data.get(key))) is not None:
                break
        if alignment is None:
            return False

        if widget not in self._styled_text_alignment_widgets:
            current_alignment = getattr(widget, 'alignment', None)
            if callable(current_alignment):
                try:
                    self._styled_text_alignment_widgets[widget] = int(current_alignment())
                except RuntimeError:
                    self._styled_text_alignment_widgets[widget] = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        set_alignment(alignment)
        return True

    def _apply_text_focus_alignment_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False

        set_focus_alignments = getattr(widget, 'set_focus_alignments', None)
        clear_focus_alignments = getattr(widget, 'clear_focus_alignments', None)
        if not callable(set_focus_alignments):
            return False

        align_data = data.get('align', data.get('alignment'))
        align_state_data = align_data if isinstance(align_data, dict) else {}
        focused = self._style_normalizer.normalize_alignment(align_state_data.get('focused'))
        unfocused = self._style_normalizer.normalize_alignment(align_state_data.get('unfocused'))
        if focused is None and unfocused is None:
            if (
                ('align' in data or 'alignment' in data) and
                widget in self._styled_text_focus_alignment_widgets and
                callable(clear_focus_alignments)
            ):
                clear_focus_alignments()
                self._styled_text_focus_alignment_widgets.discard(widget)
                return True
            return False

        set_focus_alignments(focused=focused, unfocused=unfocused)
        self._styled_text_focus_alignment_widgets.add(widget)
        return True

    def _apply_line_edit_text_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False

        set_line_edit_text_theme = getattr(widget, 'set_line_edit_text_theme', None)
        if not callable(set_line_edit_text_theme):
            return False

        raw_text_color = data.get('color')
        raw_placeholder_color = data.get('placeholder_color', data.get('placeholder-color'))
        if raw_text_color is None and raw_placeholder_color is None:
            return False

        if widget not in self._styled_line_edit_text_widgets:
            self._styled_line_edit_text_widgets[widget] = QPalette(widget.palette())

        set_line_edit_text_theme(
            text_color=to_qcolor(raw_text_color),
            placeholder_color=to_qcolor(raw_placeholder_color),
        )
        return True

    def _apply_text_font_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict) or 'font' not in data:
            return False

        font_data = data.get('font')
        if font_data is False or font_data is None:
            if widget in self._styled_text_font_widgets:
                widget.setFont(QFont(self._styled_text_font_widgets[widget]))
                widget.updateGeometry()
                widget.update()
                return True
            return False

        if not isinstance(font_data, dict):
            return False

        font = QFont(widget.font())
        changed = False

        family = self._font_family_for_qfont(font_data.get('family'))
        if family:
            font.setFamily(family)
            changed = True

        if self._apply_font_size(font, font_data.get('size')):
            changed = True

        if self._apply_font_weight(font, font_data.get('weight')):
            changed = True

        if self._apply_font_style(font, font_data.get('style')):
            changed = True

        if not changed:
            return False

        if widget not in self._styled_text_font_widgets:
            self._styled_text_font_widgets[widget] = QFont(widget.font())

        widget.setFont(font)
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

    def _apply_font_size(self, font: QFont, value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False

        if isinstance(value, str) and value.strip().lower().endswith('pt'):
            point_size = self._style_normalizer.normalize_float(value.strip()[:-2])
            if point_size is None or point_size <= 0:
                return False
            font.setPointSizeF(point_size)
            return True

        pixel_size = self._style_normalizer.normalize_int(value)
        if pixel_size is None or pixel_size <= 0:
            return False

        font.setPixelSize(pixel_size)
        return True

    def _apply_font_weight(self, font: QFont, value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False

        if isinstance(value, str):
            key = value.strip().lower()
            weights = {
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
            }
            if key in weights:
                font.setWeight(weights[key])
                return True

        weight = self._style_normalizer.normalize_int(value)
        if weight is None:
            return False

        font.setWeight(QFont.Weight(max(1, min(1000, weight))))
        return True

    def _apply_font_style(self, font: QFont, value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False

        style = str(value).strip().lower()
        if not style:
            return False

        font.setItalic(style in {'italic', 'oblique'})
        return True

    def _apply_shadow_effect_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict) or 'shadow' not in data:
            return False

        shadow = self._style_normalizer.normalize_shadow(data.get('shadow'))
        if shadow is None:
            widget.setGraphicsEffect(None)
            self._styled_effect_widgets.add(widget)
            return True

        effect = QGraphicsDropShadowEffect(widget)
        effect.setColor(shadow['color'])
        effect.setBlurRadius(float(shadow['blur']))
        effect.setOffset(shadow['offset'])
        widget.setGraphicsEffect(effect)
        self._styled_effect_widgets.add(widget)
        return True

    def _apply_text_shadow_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict) or 'shadow' not in data:
            return False

        set_text_shadow = getattr(widget, 'set_text_shadow', None)
        if not callable(set_text_shadow):
            return False

        shadow = self._style_normalizer.normalize_shadow(data.get('shadow'))
        if shadow is None:
            clear_text_shadow = getattr(widget, 'clear_text_shadow', None)
            if callable(clear_text_shadow):
                clear_text_shadow()
                self._styled_text_shadow_widgets.add(widget)
                return True
            return False

        offset = shadow['offset']
        set_text_shadow(
            color=shadow['color'],
            x=float(offset.x()),
            y=float(offset.y()),
            blur=float(shadow['blur']),
        )
        self._styled_text_shadow_widgets.add(widget)
        return True

    def _apply_text_border_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict) or 'border' not in data:
            return False

        set_text_border = getattr(widget, 'set_text_border', None)
        if not callable(set_text_border):
            return False

        border = data.get('border')
        if border is False or border is None:
            clear_text_border = getattr(widget, 'clear_text_border', None)
            if callable(clear_text_border):
                clear_text_border()
                self._styled_text_border_widgets.add(widget)
                return True
            return False

        if not isinstance(border, dict):
            return False

        color = to_qcolor(border.get('color', '#000000'))
        width = self._style_normalizer.normalize_float(border.get('width', 1.0))
        style = str(border.get('style', 'solid') or 'solid').strip()
        if color is None or width is None or width <= 0.0 or color.alpha() <= 0:
            clear_text_border = getattr(widget, 'clear_text_border', None)
            if callable(clear_text_border):
                clear_text_border()
                self._styled_text_border_widgets.add(widget)
                return True
            return False

        set_text_border(color=color, width=width, style=style)
        self._styled_text_border_widgets.add(widget)
        return True

    def _apply_text_icon_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict) or 'icon' not in data:
            return False

        set_text_icon = getattr(widget, 'set_text_icon', None)
        clear_text_icon = getattr(widget, 'clear_text_icon', None)
        capture_default_text_icon_state = getattr(widget, 'capture_default_text_icon_state', None)
        restore_default_text_icon_state = getattr(widget, 'restore_default_text_icon_state', None)
        text_icon_state = getattr(widget, 'text_icon_state', None)
        default_text_icon_state = getattr(widget, 'default_text_icon_state', None)
        if not callable(set_text_icon):
            return False
        if callable(capture_default_text_icon_state):
            capture_default_text_icon_state()

        icon = data.get('icon')
        if icon is False or icon is None:
            if callable(clear_text_icon):
                clear_text_icon()
                self._styled_text_icon_widgets.add(widget)
                return True
            return False

        if isinstance(icon, str):
            icon = {'source': icon}
        if not isinstance(icon, dict):
            return False

        source = icon.get('source', icon.get('path', icon.get('file')))
        if not isinstance(source, str) or not source.strip():
            current_icon = text_icon_state() if callable(text_icon_state) else None
            default_icon = default_text_icon_state() if callable(default_text_icon_state) else None
            if isinstance(current_icon, dict):
                source = current_icon.get('source')
            if (not isinstance(source, str) or not source.strip()) and isinstance(default_icon, dict):
                source = default_icon.get('source')
            if not isinstance(source, str) or not source.strip():
                return False

        current_icon = text_icon_state() if callable(text_icon_state) else None
        default_icon = default_text_icon_state() if callable(default_text_icon_state) else None

        resolved_source = self._qss_builder.resolve_media_source(source)
        size = self._normalize_icon_size(icon)
        if size is None:
            if isinstance(current_icon, dict):
                size = current_icon.get('size')
            elif isinstance(default_icon, dict):
                size = default_icon.get('size')
        spacing = self._style_normalizer.normalize_float(icon.get('spacing'))
        if spacing is None:
            if isinstance(current_icon, dict):
                spacing = current_icon.get('spacing')
            elif isinstance(default_icon, dict):
                spacing = default_icon.get('spacing')
            spacing = float(spacing) if isinstance(spacing, (int, float)) else 4.0
        color = to_qcolor(icon.get('color'))
        align = icon.get('align', icon.get('side'))
        if not isinstance(align, str) or not align.strip():
            if isinstance(current_icon, dict):
                align = current_icon.get('align')
            elif isinstance(default_icon, dict):
                align = default_icon.get('align')
        if not isinstance(align, str) or not align.strip():
            align = 'left'
        applied = bool(set_text_icon(
            source=resolved_source,
            align=str(align),
            size=size,
            spacing=spacing,
            color=color,
        ))
        if applied:
            self._styled_text_icon_widgets.add(widget)
        elif callable(restore_default_text_icon_state):
            restore_default_text_icon_state()
            self._styled_text_icon_widgets.add(widget)
            applied = True
        return applied

    def _apply_text_spacing_theme(self, widget: QWidget, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False

        raw_spacing = data.get('spacing', data.get('letter_spacing', data.get('letter-spacing')))
        if raw_spacing is None:
            return False

        set_text_spacing = getattr(widget, 'set_text_spacing', None)
        clear_text_spacing = getattr(widget, 'clear_text_spacing', None)
        if not callable(set_text_spacing):
            return False

        if raw_spacing is False:
            if callable(clear_text_spacing):
                clear_text_spacing()
                self._styled_text_spacing_widgets.add(widget)
                return True
            return False

        spacing = self._style_normalizer.normalize_float(raw_spacing)
        if spacing is None:
            return False

        set_text_spacing(spacing)
        self._styled_text_spacing_widgets.add(widget)
        return True

    def _normalize_icon_size(self, data: dict[str, Any]) -> QSize | None:
        if not isinstance(data, dict):
            return None

        raw_size = data.get('size')
        if isinstance(raw_size, (list, tuple)) and len(raw_size) >= 2:
            width = self._style_normalizer.normalize_int(raw_size[0])
            height = self._style_normalizer.normalize_int(raw_size[1])
        elif isinstance(raw_size, dict):
            width = self._style_normalizer.normalize_int(raw_size.get('width', raw_size.get('w')))
            height = self._style_normalizer.normalize_int(raw_size.get('height', raw_size.get('h')))
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

    def _apply_layout_justify(self, layout: QLayout, original: dict[str, Any], justify: str) -> None:
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
                    if layout.itemAt(index) is not None and layout.itemAt(index).spacerItem() is None
                ]
                for position in reversed(widget_positions[:-1]):
                    insert_index = position + 1
                    layout.insertStretch(insert_index, 1)
                    indices.append(insert_index)
                indices.sort(reverse=True)
        original['justify_indices'] = indices

    def _clear_layout_justify(self, layout: QLayout, original: dict[str, Any]) -> None:
        indices = original.get('justify_indices')
        if not isinstance(indices, list):
            original['justify_indices'] = []
            return

        for index in sorted({int(value) for value in indices if isinstance(value, int)}, reverse=True):
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
