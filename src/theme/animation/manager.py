from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import replace
from time import monotonic
from typing import Any, cast

from PySide6.QtCore import (
    QAbstractAnimation,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPalette, QWheelEvent
from PySide6.QtWidgets import QApplication, QAbstractButton, QAbstractScrollArea, QAbstractSlider, QLayout, QSlider, QWidget

from src.theme.colors import normalize_color, to_qcolor
from src.theme.constants import EVENT_ACTIONS
from src.theme.qss.targets import resolve_target_widgets
from src.theme.schema.access import coerce_float, object_map, theme_map
from src.ui.widgets.main.box import BoxThemeMixin
from src.ui.widgets.main.checkables import MTSwitch
from src.ui.widgets.main.containers import MTComboBox
from src.ui.widgets.main.inputs import MTSlider
from src.ui.widgets.settings.containers import MTCollapsibleContainer

from .helpers import (
    clone_gradient,
    gradient_to_qss,
    interpolate_color,
    interpolate_gradient,
    normalize_dash_border,
    normalize_gradient,
)
from .overlays import DashBorderOverlay
from .parser import parse_specs
from .timer import TimerAnimation
from .types import AnimationSpec

_RAINBOW_HANDLE_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, '#ff0000'),
    (0.07, '#ff0000'),
    (0.18, '#ff8a00'),
    (0.30, '#fff000'),
    (0.46, '#00ff66'),
    (0.62, '#00d5ff'),
    (0.78, '#4b5cff'),
    (0.92, '#ff00c8'),
    (1.00, '#ff0000'),
)
_CSS_DECLARATION_PATTERN = re.compile(r'([a-zA-Z-]+)\s*:\s*([^;{}]+)')
_RUNTIME_BORDER_FADE_STEP = 0.12

def _widget_or_none(value: QObject | QWidget) -> QWidget | None:
    return value if isinstance(value, QWidget) else None


def _slider_or_none(value: object) -> QAbstractSlider | None:
    return value if isinstance(value, QAbstractSlider) else None

class AnimationManager(QObject):
    def __init__(self, root: QWidget):
        super().__init__()
        self._root = root
        self._animations: dict[QWidget, dict[str, QParallelAnimationGroup]] = {}
        self._cache: dict[QWidget, dict[str, Any]] = {}
        self._style_overrides: dict[QWidget, dict[str, str]] = {}
        self._slider_style_overrides: dict[QWidget, dict[str, dict[str, str]]] = {}
        self._base_styles: dict[QWidget, str] = {}
        self._filtered_widgets: set[QWidget] = set()
        self._viewport_hosts: dict[QWidget, QWidget] = {}
        self._hovered_widgets: set[QWidget] = set()
        self._action_property_keys: dict[QWidget, dict[str, set[str]]] = {}
        self._action_specs: dict[QWidget, dict[str, list[AnimationSpec]]] = {}
        self._active_property_actions: dict[QWidget, dict[str, str]] = {}
        self._pending_checkable_reconcile_widgets: set[QWidget] = set()
        self._pending_hover_exit_widgets: set[QWidget] = set()
        self._paint_overlays: dict[QWidget, DashBorderOverlay] = {}
        self._paint_border_profiles: dict[QWidget, dict[str, Any]] = {}
        self._runtime_filtered_widgets: set[QWidget] = set()
        self._runtime_rainbow_widgets: set[QWidget] = set()
        self._runtime_native_border_widgets: dict[QWidget, dict[str, Any]] = {}
        self._runtime_hover_overlays: dict[QWidget, DashBorderOverlay] = {}
        self._runtime_hover_overlay_states: dict[QWidget, dict[str, float]] = {}
        self._runtime_rainbow_duration_ms = 5000
        self._wheel_event_deltas: dict[QWidget, dict[str, float]] = {}
        self._locked_tabs: set[QWidget] = set()
        self._tab_toggle_slots: dict[QWidget, Any] = {}
        self._toggle_action_slots: dict[QWidget, Any] = {}
        self._popup_action_slots: dict[QWidget, tuple[Any, Any]] = {}
        
        self._shared_rainbow_epoch = monotonic()
        self._shared_rainbow_bindings: dict[QWidget, tuple[int, float]] = {}
        self._shared_widget_border_bindings: dict[QWidget, tuple[int, float, float, float]] = {}
        self._shared_border_color_bindings: dict[DashBorderOverlay, tuple[int, float, float, float]] = {}
        self._shared_gradient_border_bindings: dict[DashBorderOverlay, tuple[int, float]] = {}
        
        self._shared_rainbow_timer = QTimer(self)
        self._shared_rainbow_timer.setInterval(16)
        self._shared_rainbow_timer.timeout.connect(self._update_shared_rainbow_widgets)
        
        self._hover_reconcile_timer = QTimer(self)
        self._hover_reconcile_timer.setInterval(16)
        self._hover_reconcile_timer.timeout.connect(self._reconcile_hover_states)

    def load(self, animations: dict[str, Any], theme_widgets: dict[str, Any] | None = None) -> None:
        self._clear()
        theme_widgets_map = theme_widgets or {}
        for target, raw_specs in animations.items():
            specs = parse_specs(raw_specs)
            if not specs:
                continue

            widgets = resolve_target_widgets(self._root, target, include_window=True)
            if not widgets:
                continue

            base_styles = theme_map(theme_widgets_map.get(target)) or {}

            for widget in widgets:
                self._register_widget(widget)
                action_groups = self._animations[widget]
                effective_specs = [
                    *specs,
                    *self._build_auto_leave_specs(widget, specs, base_styles),
                ]
                animated_content_height = any(
                    spec.property_key == 'parts.content.height' and spec.action in {'checked', 'unchecked'}
                    for spec in effective_specs
                )
                animated_arrow_rotation = any(
                    spec.property_key == 'parts.icon.rotation' and spec.action in {'checked', 'unchecked'}
                    for spec in effective_specs
                )
                widget.setProperty('_themeAnimatedContentHeight', animated_content_height)
                widget.setProperty('_themeAnimatedArrowRotation', animated_arrow_rotation)
                for spec in effective_specs:
                    group = action_groups.setdefault(spec.action, QParallelAnimationGroup(widget))
                    self._append_animation(widget, spec, group, base_styles)

                popup_close_duration = max(
                    (
                        spec.duration
                        for spec in effective_specs
                        if spec.action == 'close' and spec.property_key.startswith(('parts.popup.', 'parts.item.'))
                    ),
                    default=0,
                )
                widget.setProperty('_themePopupCloseDelayMs', int(popup_close_duration))

                always_group = action_groups.get('always')
                if always_group is not None and always_group.state() != QAbstractAnimation.State.Running:
                    always_group.start()

                self._sync_initial_state_actions(widget)
                self._queue_widget_style_refresh(widget)

    def _build_auto_leave_specs(
        self,
        widget: QWidget,
        specs: list[AnimationSpec],
        base_styles: dict[str, Any],
    ) -> list[AnimationSpec]:
        if any(spec.action == 'leave' for spec in specs):
            return []

        auto_specs: list[AnimationSpec] = []
        for spec in specs:
            if spec.action != 'hover':
                continue

            end_value = self._sample_base_animation_value(widget, base_styles, spec)
            if end_value is None:
                continue

            auto_specs.append(
                replace(
                    spec,
                    action='leave',
                    start=deepcopy(spec.end),
                    end=end_value,
                )
            )
        return auto_specs

    def _sample_base_animation_value(
        self,
        widget: QWidget,
        base_styles: dict[str, Any],
        spec: AnimationSpec,
    ) -> Any | None:
        match spec.kind:
            case 'color':
                color = self._sample_style_color(base_styles, spec.property_key)
                if isinstance(color, QColor):
                    return QColor(color)
                color = self._sample_override_color(widget, spec.css_property)
                if isinstance(color, QColor):
                    return QColor(color)
                return self._sample_color(widget, spec.css_property, fallback=QColor(Qt.GlobalColor.transparent))
            case 'number':
                try:
                    return float(self._sample_number(widget, spec.property_key, fallback=float(spec.start or 0.0)))
                except (TypeError, ValueError):
                    return None
            case 'gradient':
                fallback = theme_map(spec.start) or theme_map(spec.end)
                if fallback is None:
                    return None
                gradient = self._sample_style_gradient(base_styles, spec.property_key, fallback=fallback)
                return clone_gradient(gradient) if isinstance(gradient, dict) else None
            case _:
                return None
        return None

    def eventFilter(self, obj: QObject, event: QEvent):
        obj_widget = _widget_or_none(obj)
        host_widget = self._viewport_hosts.get(obj_widget) if obj_widget is not None else None
        target_widget = host_widget or obj_widget

        if obj_widget is not None:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
                self._sync_paint_overlay_geometry(obj_widget)
                self._sync_runtime_overlay_geometry(obj_widget)
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show) and self._style_overrides.get(obj_widget):
                    self._apply_widget_style(obj_widget)
            elif event.type() == QEvent.Type.Hide:
                if (overlay := self._paint_overlays.get(obj_widget)) is not None:
                    overlay.hide()
                if (overlay := self._runtime_hover_overlays.get(obj_widget)) is not None:
                    overlay.hide()
            elif event.type() == QEvent.Type.Enter:
                self._hovered_widgets.add(obj_widget)
                if obj_widget in self._runtime_native_border_widgets:
                    self._runtime_native_border_widgets[obj_widget]['target_opacity'] = 1.0
                if (overlay := self._runtime_hover_overlays.get(obj_widget)) is not None:
                    state = self._runtime_hover_overlay_states.setdefault(
                        obj_widget, {'opacity': 0.0, 'target_opacity': 0.0}
                    )
                    state['target_opacity'] = 1.0
                    if obj_widget.isVisible():
                        overlay.show()
            elif event.type() == QEvent.Type.Leave:
                self._hovered_widgets.discard(obj_widget)
                if obj_widget in self._runtime_native_border_widgets:
                    self._runtime_native_border_widgets[obj_widget]['target_opacity'] = 0.0
                if (overlay := self._runtime_hover_overlays.get(obj_widget)) is not None:
                    state = self._runtime_hover_overlay_states.setdefault(
                        obj_widget, {'opacity': 0.0, 'target_opacity': 0.0}
                    )
                    state['target_opacity'] = 0.0

        if target_widget is None or target_widget not in self._animations:
            return super().eventFilter(obj, event)

        if (
            isinstance(event, QMouseEvent) and
            event.type() in {
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
            } and
            event.button() != Qt.MouseButton.LeftButton
        ):
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.Wheel and isinstance(event, QWheelEvent):
            if self._handle_wheel_event(target_widget, event):
                return True

        action = EVENT_ACTIONS.get(event.type())
        if action:
            self._play(target_widget, action)
            if action in {'hover', 'leave'}:
                self._start_hover_reconcile_timer()
            if action in {'hover', 'leave', 'press', 'release'}:
                self._queue_checkable_reconcile(target_widget)
        elif event.type() == QEvent.Type.EnabledChange:
            self._play(target_widget, 'enabled' if target_widget.isEnabled() else 'disabled')

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            release_rect_widget = obj_widget or target_widget
            if event.button() == Qt.MouseButton.LeftButton and release_rect_widget.rect().contains(event.position().toPoint()):
                self._play(target_widget, 'click')
            self._queue_checkable_reconcile(target_widget)

        if (
            event.type() == QEvent.Type.MouseButtonDblClick and
            isinstance(event, QMouseEvent) and
            event.button() == Qt.MouseButton.LeftButton
        ):
            self._play(target_widget, 'double_click')
            self._queue_checkable_reconcile(target_widget)

        return super().eventFilter(obj, event)

    def _clear(self) -> None:
        self._clear_runtime_rainbow_mode()
        shared_rainbow_widgets = set(self._shared_rainbow_bindings)

        for widget, slot in self._tab_toggle_slots.items():
            if not isinstance(widget, QAbstractButton):
                continue
            try:
                widget.toggled.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

        for widget, slot in self._toggle_action_slots.items():
            if not isinstance(widget, QAbstractButton):
                continue
            try:
                widget.toggled.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

        for widget, slots in self._popup_action_slots.items():
            if not isinstance(widget, MTComboBox):
                continue
            open_slot, close_slot = slots
            try:
                widget.popupOpened.disconnect(open_slot)
            except (RuntimeError, TypeError):
                pass
            try:
                widget.popupClosed.disconnect(close_slot)
            except (RuntimeError, TypeError):
                pass

        for widget, groups in self._animations.items():
            for group in groups.values():
                group.stop()

            self._reset_widget_animation_state(widget, had_shared_rainbow=widget in shared_rainbow_widgets)
            try:
                widget.setProperty('_themeAnimatedContentHeight', False)
                widget.setProperty('_themeAnimatedArrowRotation', False)
                widget.setProperty('_themePopupCloseDelayMs', 0)
            except RuntimeError:
                pass

            if widget in self._filtered_widgets:
                widget.removeEventFilter(self)

            viewport = self._viewport_for_widget(widget)
            if viewport is not None:
                viewport.removeEventFilter(self)

            if widget in self._base_styles:
                widget.setStyleSheet(self._base_styles[widget])
                widget.setProperty('_themeAnimationStyleManaged', False)

            if (overlay := self._paint_overlays.get(widget)) is not None:
                overlay.hide()
                overlay.deleteLater()

        self._animations.clear()
        self._cache.clear()
        self._style_overrides.clear()
        self._slider_style_overrides.clear()
        self._base_styles.clear()
        self._filtered_widgets.clear()
        self._viewport_hosts.clear()
        self._hovered_widgets.clear()
        self._action_property_keys.clear()
        self._action_specs.clear()
        self._active_property_actions.clear()
        self._pending_checkable_reconcile_widgets.clear()
        self._pending_hover_exit_widgets.clear()
        self._paint_overlays.clear()
        self._paint_border_profiles.clear()
        self._hover_reconcile_timer.stop()
        self._locked_tabs.clear()
        self._tab_toggle_slots.clear()
        self._toggle_action_slots.clear()
        self._popup_action_slots.clear()
        self._shared_rainbow_bindings.clear()
        self._shared_border_color_bindings.clear()
        self._shared_gradient_border_bindings.clear()
        self._shared_rainbow_timer.stop()

    def set_runtime_rainbow_mode(self, enabled: bool, duration_ms: int | float) -> None:
        self._clear_runtime_rainbow_mode()
        if not enabled:
            return

        duration = max(1, int(round(float(duration_ms))))
        self._runtime_rainbow_duration_ms = duration

        for widget in resolve_target_widgets(self._root, 'MTSwitch', include_window=True):
            if not isinstance(widget, MTSwitch):
                continue
            if widget.property('rainbowBorderExcluded') is True:
                continue
            if widget.property('rainbowBorderTarget') is False:
                continue
            if not widget.has_visible_parts_theme():
                self._reset_widget_animation_state(widget, had_shared_rainbow=True)
                continue
            self._ensure_runtime_widget_filter(widget)
            self._runtime_rainbow_widgets.add(widget)
            if widget.isChecked():
                self._set_shared_rainbow_active(widget, duration, 0.0, True)
            else:
                self._reset_widget_animation_state(widget, had_shared_rainbow=True)

        for widget in resolve_target_widgets(self._root, 'MTSlider', include_window=True):
            if widget.property('rainbowBorderExcluded') is True:
                continue
            if widget.property('rainbowBorderTarget') is False:
                continue
            self._ensure_runtime_widget_filter(widget)
            self._runtime_rainbow_widgets.add(widget)
            self._set_shared_rainbow_active(widget, duration, 0.0, True)

        base_color = self._sample_shared_rainbow_color(0.0, brightness=0.9, saturation=0.8)
        setting_widgets: list[QWidget] = []
        seen_setting_widgets: set[QWidget] = set()
        for target in (
            'MTComboBox',
            'MTLineEdit',
            'MTButtonSetting',
            'MTCheckBoxSetting',
            'MTSwitchSetting',
            'MTSwitchRowSetting',
            'MTPathSetting',
            'MTSliderSetting',
        ):
            for candidate in resolve_target_widgets(self._root, target, include_window=True):
                if candidate in seen_setting_widgets:
                    continue
                if candidate.property('rainbowBorderExcluded') is True:
                    continue
                if candidate.property('rainbowBorderTarget') is False:
                    continue
                seen_setting_widgets.add(candidate)
                setting_widgets.append(candidate)

        for widget in setting_widgets:
            self._ensure_runtime_widget_filter(widget)
            self._stop_runtime_conflicting_hover_groups(widget)
            if (paint_overlay := self._paint_overlays.get(widget)) is not None:
                self._set_shared_border_color_active(paint_overlay, 0, 0.0, False)
                self._set_shared_gradient_border_active(paint_overlay, 0, 0.0, False)
                try:
                    paint_overlay.hide()
                except RuntimeError:
                    pass
            border_config = self._detect_runtime_border_config(widget)
            if border_config.get('visible'):
                self._runtime_native_border_widgets[widget] = {
                    'previous_border_color_override': deepcopy(self._style_overrides.get(widget, {}).get('border-color')),
                    'base_border_color': str(border_config.get('color_text', '') or ''),
                    'opacity': 1.0 if self._cursor_over_widget(widget) else 0.0,
                    'target_opacity': 1.0 if self._cursor_over_widget(widget) else 0.0,
                }
                self._set_shared_widget_border_active(widget, duration, 0.0, True, brightness=0.9, saturation=0.8)
                continue

            overlay = self._runtime_hover_overlays.get(widget)
            if overlay is None:
                overlay = DashBorderOverlay(widget)
                self._runtime_hover_overlays[widget] = overlay
            self._runtime_hover_overlay_states[widget] = {
                'opacity': 1.0 if self._cursor_over_widget(widget) else 0.0,
                'target_opacity': 1.0 if self._cursor_over_widget(widget) else 0.0,
            }
            overlay.configure(
                color=base_color,
                width=float(border_config.get('width', 1.5)),
                radius=float(border_config.get('radius', 10.0)),
                dash_pattern=[9999.0, 1.0],
                inset=float(border_config.get('inset', 1.0)),
                pen_style=Qt.PenStyle.SolidLine,
                opacity=1.0 if self._cursor_over_widget(widget) else 0.0,
            )
            self._sync_runtime_overlay_geometry(widget)
            if widget.isVisible() and self._cursor_over_widget(widget):
                overlay.show()
            self._set_shared_border_color_active(
                overlay,
                duration,
                0.0,
                True,
                brightness=0.9,
                saturation=0.8,
            )

    def _clear_runtime_rainbow_mode(self) -> None:
        hovered_widgets = {
            widget
            for widget in (
                set(self._runtime_rainbow_widgets)
                | set(self._runtime_native_border_widgets)
                | set(self._runtime_hover_overlays)
            )
            if self._cursor_over_widget(widget)
        }
        for widget in list(self._runtime_rainbow_widgets):
            self._set_shared_rainbow_active(widget, 0, 0.0, False)
            self._reset_widget_animation_state(widget, had_shared_rainbow=True)
        self._runtime_rainbow_widgets.clear()

        for widget in list(self._runtime_native_border_widgets):
            self._set_shared_widget_border_active(widget, 0, 0.0, False)
        self._runtime_native_border_widgets.clear()

        for widget, overlay in list(self._runtime_hover_overlays.items()):
            self._set_shared_border_color_active(overlay, 0, 0.0, False)
            try:
                overlay.hide()
                overlay.deleteLater()
            except RuntimeError:
                pass
        self._runtime_hover_overlays.clear()
        self._runtime_hover_overlay_states.clear()
        self._wheel_event_deltas.clear()

        for widget in list(self._runtime_filtered_widgets):
            if widget in self._filtered_widgets:
                continue
            try:
                widget.removeEventFilter(self)
            except RuntimeError:
                pass
        self._runtime_filtered_widgets.clear()
        for widget in hovered_widgets:
            if self._cursor_over_widget(widget) and widget in self._animations:
                self._play(widget, 'hover')
        self._stop_shared_rainbow_timer_if_idle()

    def _ensure_runtime_widget_filter(self, widget: QWidget) -> None:
        if widget in self._filtered_widgets or widget in self._runtime_filtered_widgets:
            return
        widget.installEventFilter(self)
        self._runtime_filtered_widgets.add(widget)

    def _sync_runtime_overlay_geometry(self, widget: QWidget) -> None:
        overlay = self._runtime_hover_overlays.get(widget)
        if overlay is None:
            return
        was_visible = overlay.isVisible()
        overlay.setGeometry(widget.rect())
        overlay.raise_()
        if was_visible and widget.isVisible():
            overlay.show()

    def _stop_runtime_conflicting_hover_groups(self, widget: QWidget) -> None:
        groups = self._animations.get(widget)
        if not isinstance(groups, dict):
            return
        for action in ('hover', 'leave'):
            group = groups.get(action)
            if group is None:
                continue
            try:
                group.stop()
            except RuntimeError:
                continue

    def _reset_widget_animation_state(self, widget: QWidget, *, had_shared_rainbow: bool = False) -> None:
        cache = self._cache.get(widget, {})
        if not had_shared_rainbow and not {'parts.handle.rainbow', 'parts.sub_page.rainbow'} & set(cache):
            return

        if isinstance(widget, MTSlider):
            try:
                widget.clear_slider_line_rainbow()
                widget.update()
            except RuntimeError:
                return
            return
        if isinstance(widget, MTSwitch):
            try:
                widget.clear_handle_rainbow()
                widget.update()
            except RuntimeError:
                return

    def _register_widget(self, widget: QWidget) -> None:
        self._animations.setdefault(widget, {})
        self._cache.setdefault(widget, {})
        self._style_overrides.setdefault(widget, {})
        self._slider_style_overrides.setdefault(widget, {})
        base_style = '' if widget.property('_themeAnimationStyleManaged') is True else widget.styleSheet()
        self._base_styles.setdefault(widget, base_style)

        if widget not in self._filtered_widgets:
            widget.installEventFilter(self)
            self._filtered_widgets.add(widget)
        viewport = self._viewport_for_widget(widget)
        if viewport is not None and viewport not in self._viewport_hosts:
            viewport.installEventFilter(self)
            self._viewport_hosts[viewport] = widget

        self._bind_tab_toggle(widget)
        self._bind_toggle_action(widget)
        self._bind_popup_actions(widget)
        if self._is_locked_tab(widget):
            self._locked_tabs.add(widget)

    def _viewport_for_widget(self, widget: QWidget) -> QWidget | None:
        if not isinstance(widget, QAbstractScrollArea):
            return None
        try:
            return widget.viewport()
        except RuntimeError:
            return None

    def _bind_tab_toggle(self, widget: QWidget) -> None:
        if not bool(widget.property('pageTab')) or not isinstance(widget, QAbstractButton):
            return
        if widget in self._tab_toggle_slots:
            return

        def slot(checked: object) -> None:
            self._on_tab_toggled(widget, bool(checked))
        self._tab_toggle_slots[widget] = slot
        widget.toggled.connect(slot)

    def _bind_toggle_action(self, widget: QWidget) -> None:
        if bool(widget.property('pageTab')) or not isinstance(widget, QAbstractButton):
            return
        if not widget.isCheckable() or widget in self._toggle_action_slots:
            return

        def slot(checked: object) -> None:
            self._on_widget_toggled(widget, bool(checked))
        self._toggle_action_slots[widget] = slot
        widget.toggled.connect(slot)

    def _bind_popup_actions(self, widget: QWidget) -> None:
        if not isinstance(widget, MTComboBox) or widget in self._popup_action_slots:
            return

        def open_slot() -> None:
            self._play(widget, 'open')

        def close_slot() -> None:
            self._play(widget, 'close')
        self._popup_action_slots[widget] = (open_slot, close_slot)
        widget.popupOpened.connect(open_slot)
        widget.popupClosed.connect(close_slot)

    def _on_widget_toggled(self, widget: QWidget, checked: bool) -> None:
        self._play_checkable_state(widget, force=True)
        self._queue_checkable_reconcile(widget)
        if widget in self._runtime_rainbow_widgets:
            if checked:
                self._set_shared_rainbow_active(widget, self._runtime_rainbow_duration_ms, 0.0, True)
            else:
                self._set_shared_rainbow_active(widget, 0, 0.0, False)
                self._reset_widget_animation_state(widget, had_shared_rainbow=True)

    def _on_tab_toggled(self, widget: QWidget, checked: bool) -> None:
        self._play_checkable_state(widget, force=True)
        self._queue_checkable_reconcile(widget)

        if checked:
            self._locked_tabs.add(widget)
            return

        self._locked_tabs.discard(widget)
        if 'unchecked' in self._animations.get(widget, {}):
            return

        if (overrides := self._style_overrides.get(widget)):
            overrides.clear()
        self._apply_widget_style(widget)

    def _is_locked_tab(self, widget: QWidget) -> bool:
        if not bool(widget.property('pageTab')) or not isinstance(widget, QAbstractButton):
            return False
        return bool(widget.isCheckable() and widget.isChecked())

    def _sync_initial_state_actions(self, widget: QWidget) -> None:
        groups = self._animations.get(widget)
        if not groups:
            return

        if not widget.isEnabled() and 'disabled' in groups:
            self._apply_action_final_state(widget, 'disabled')
            return

        if widget.isEnabled() and 'enabled' in groups:
            self._apply_action_final_state(widget, 'enabled')

        if not isinstance(widget, QAbstractButton):
            return
        if not widget.isCheckable():
            return

        action = self._resolve_checkable_state_action(widget, groups)
        if action is None:
            return

        self._apply_action_final_state(widget, action)

    def _queue_widget_style_refresh(self, widget: QWidget) -> None:
        if not self._style_overrides.get(widget) and not self._slider_style_overrides.get(widget):
            return

        def refresh_style() -> None:
            if widget in self._animations:
                self._apply_widget_style(widget)

        QTimer.singleShot(0, refresh_style)

    def _sync_paint_overlay_geometry(self, widget: QWidget) -> None:
        overlay = self._paint_overlays.get(widget)
        if overlay is None:
            return

        was_visible = overlay.isVisible()
        overlay.setGeometry(widget.rect())
        overlay.raise_()
        if was_visible and widget.isVisible():
            overlay.show()

    def _shared_rainbow_value(self, duration_ms: int | float, phase_offset: float = 0.0) -> float:
        try:
            duration = float(duration_ms)
        except (TypeError, ValueError):
            return 0.0
        if duration <= 0.0:
            return 0.0
        elapsed_ms = (monotonic() - self._shared_rainbow_epoch) * 1000.0
        return float(((elapsed_ms / duration) + float(phase_offset)) % 1.0)

    def _set_shared_rainbow_active(self, widget: QWidget, duration_ms: int | float, phase_offset: float, active: bool) -> None:
        if active:
            duration = max(1, int(round(float(duration_ms))))
            self._shared_rainbow_bindings[widget] = (duration, float(phase_offset))
            self._update_shared_rainbow_widget(widget, duration, float(phase_offset))
            self._ensure_shared_rainbow_timer()
            return

        self._shared_rainbow_bindings.pop(widget, None)
        self._stop_shared_rainbow_timer_if_idle()

    def _set_shared_widget_border_active(self, widget: QWidget, duration_ms: int | float, phase_offset: float, active: bool, brightness: float = 1.0, saturation: float = 1.0) -> None:
        if active:
            duration = max(1, int(round(float(duration_ms))))
            brightness = max(0.0, min(float(brightness), 1.0))
            saturation = max(0.0, min(float(saturation), 1.0))
            self._shared_widget_border_bindings[widget] = (duration, float(phase_offset), brightness, saturation)
            self._apply_runtime_widget_border_color(
                widget,
                self._sample_shared_rainbow_color(self._shared_rainbow_value(duration, phase_offset), brightness=brightness, saturation=saturation),
            )
            self._ensure_shared_rainbow_timer()
            return

        self._shared_widget_border_bindings.pop(widget, None)
        self._restore_runtime_widget_border(widget)
        self._stop_shared_rainbow_timer_if_idle()

    def _set_shared_border_color_active(self, overlay: DashBorderOverlay, duration_ms: int | float, phase_offset: float, active: bool, brightness: float = 1.0, saturation: float = 1.0) -> None:
        if active:
            duration = max(1, int(round(float(duration_ms))))
            brightness = max(0.0, min(float(brightness), 1.0))
            saturation = max(0.0, min(float(saturation), 1.0))
            self._shared_border_color_bindings[overlay] = (duration, float(phase_offset), brightness, saturation)
            overlay.set_color(self._sample_shared_rainbow_color(self._shared_rainbow_value(duration, phase_offset), brightness=brightness, saturation=saturation))
            self._ensure_shared_rainbow_timer()
            return

        self._shared_border_color_bindings.pop(overlay, None)
        self._stop_shared_rainbow_timer_if_idle()

    def _set_shared_gradient_border_active(self, overlay: DashBorderOverlay, duration_ms: int | float, phase_offset: float, active: bool) -> None:
        if active:
            duration = max(1, int(round(float(duration_ms))))
            self._shared_gradient_border_bindings[overlay] = (duration, float(phase_offset))
            overlay.set_gradient_phase(self._shared_rainbow_value(duration, phase_offset))
            self._ensure_shared_rainbow_timer()
            return

        self._shared_gradient_border_bindings.pop(overlay, None)
        self._stop_shared_rainbow_timer_if_idle()

    def _ensure_shared_rainbow_timer(self) -> None:
        if not self._shared_rainbow_timer.isActive():
            self._shared_rainbow_timer.start()

    def _stop_shared_rainbow_timer_if_idle(self) -> None:
        if not self._shared_rainbow_bindings and not self._shared_widget_border_bindings and not self._shared_border_color_bindings and not self._shared_gradient_border_bindings:
            self._shared_rainbow_timer.stop()

    def _update_shared_rainbow_widget(self, widget: QWidget, duration_ms: int | float, phase_offset: float) -> None:
        phase = self._shared_rainbow_value(duration_ms, phase_offset)
        self._set_shared_widget_rainbow_phase(widget, phase)

    def _sample_shared_rainbow_color(self, phase: float, *, brightness: float = 1.0, saturation: float = 1.0) -> QColor:
        normalized = float(phase) % 1.0
        previous_offset, previous_color = _RAINBOW_HANDLE_STOPS[0]
        color = QColor(_RAINBOW_HANDLE_STOPS[-1][1])
        for next_offset, next_color in _RAINBOW_HANDLE_STOPS[1:]:
            if normalized <= next_offset:
                span = max(next_offset - previous_offset, 1e-9)
                mix = max(0.0, min(1.0, (normalized - previous_offset) / span))
                start = QColor(previous_color)
                end = QColor(next_color)
                color = QColor(
                    round(start.red() + (end.red() - start.red()) * mix),
                    round(start.green() + (end.green() - start.green()) * mix),
                    round(start.blue() + (end.blue() - start.blue()) * mix),
                    round(start.alpha() + (end.alpha() - start.alpha()) * mix),
                )
                break
            previous_offset, previous_color = next_offset, next_color

        saturation = max(0.0, min(float(saturation), 1.0))
        if saturation < 0.999:
            gray = round((color.red() * 0.299) + (color.green() * 0.587) + (color.blue() * 0.114))
            color = QColor(
                round(gray + (color.red() - gray) * saturation),
                round(gray + (color.green() - gray) * saturation),
                round(gray + (color.blue() - gray) * saturation),
                color.alpha(),
            )

        brightness = max(0.0, min(float(brightness), 1.0))
        if brightness < 0.999:
            color = QColor(
                round(color.red() * brightness),
                round(color.green() * brightness),
                round(color.blue() * brightness),
                color.alpha(),
            )
        return color

    def _set_shared_widget_rainbow_phase(self, widget: QWidget, phase: float) -> None:
        if isinstance(widget, MTSlider):
            widget.set_slider_line_rainbow(float(phase))
            self._cache.setdefault(widget, {})['parts.sub_page.rainbow'] = float(phase)
            return

        if isinstance(widget, MTSwitch):
            widget.set_handle_rainbow(float(phase))
            self._cache.setdefault(widget, {})['parts.handle.rainbow'] = float(phase)

    def _update_shared_rainbow_widgets(self) -> None:
        stale_widgets: list[QWidget] = []
        stale_border_widgets: list[QWidget] = []
        stale_color_overlays: list[DashBorderOverlay] = []
        stale_overlays: list[DashBorderOverlay] = []
        phase_cache: dict[tuple[int, float], float] = {}
        for widget, (duration, phase_offset) in list(self._shared_rainbow_bindings.items()):
            try:
                cache_key = (duration, float(phase_offset))
                phase = phase_cache.get(cache_key)
                if phase is None:
                    phase = self._shared_rainbow_value(duration, phase_offset)
                    phase_cache[cache_key] = phase
                self._set_shared_widget_rainbow_phase(widget, phase)
            except RuntimeError:
                stale_widgets.append(widget)
        for widget in list(self._shared_widget_border_bindings):
            if widget.parentWidget() is None and widget is not self._root:
                stale_border_widgets.append(widget)
        for overlay, (duration, phase_offset, brightness, saturation) in list(self._shared_border_color_bindings.items()):
            try:
                cache_key = (duration, float(phase_offset))
                phase = phase_cache.get(cache_key)
                if phase is None:
                    phase = self._shared_rainbow_value(duration, phase_offset)
                    phase_cache[cache_key] = phase
                overlay.set_color(self._sample_shared_rainbow_color(phase, brightness=brightness, saturation=saturation))
            except RuntimeError:
                stale_color_overlays.append(overlay)
        for overlay, (duration, phase_offset) in list(self._shared_gradient_border_bindings.items()):
            try:
                cache_key = (duration, float(phase_offset))
                phase = phase_cache.get(cache_key)
                if phase is None:
                    phase = self._shared_rainbow_value(duration, phase_offset)
                    phase_cache[cache_key] = phase
                overlay.set_gradient_phase(phase)
            except RuntimeError:
                stale_overlays.append(overlay)
        self._update_runtime_hover_states()
        for widget in stale_widgets:
            self._shared_rainbow_bindings.pop(widget, None)
        for widget in stale_border_widgets:
            self._shared_widget_border_bindings.pop(widget, None)
            self._restore_runtime_widget_border(widget)
        for overlay in stale_color_overlays:
            self._shared_border_color_bindings.pop(overlay, None)
        for overlay in stale_overlays:
            self._shared_gradient_border_bindings.pop(overlay, None)
        self._stop_shared_rainbow_timer_if_idle()

    def _update_runtime_hover_states(self) -> None:
        for widget, state in list(self._runtime_native_border_widgets.items()):
            try:
                current = float(state.get('opacity', 0.0))
                target = 1.0 if self._cursor_over_widget(widget) else 0.0
                state['target_opacity'] = target
                next_opacity = self._step_runtime_opacity(current, target)
                state['opacity'] = next_opacity
                if next_opacity <= 0.001:
                    self._restore_runtime_widget_border(widget)
                else:
                    duration, phase_offset, brightness, saturation = self._shared_widget_border_bindings.get(widget, (self._runtime_rainbow_duration_ms, 0.0, 0.9, 0.8))
                    phase = self._shared_rainbow_value(duration, phase_offset)
                    self._apply_runtime_widget_border_color(
                        widget,
                        self._sample_shared_rainbow_color(phase, brightness=brightness, saturation=saturation),
                        opacity=next_opacity,
                    )
            except RuntimeError:
                continue

        for widget, overlay in list(self._runtime_hover_overlays.items()):
            state = self._runtime_hover_overlay_states.get(widget)
            if state is None:
                continue
            try:
                current = float(state.get('opacity', 0.0))
                target = 1.0 if self._cursor_over_widget(widget) else 0.0
                state['target_opacity'] = target
                next_opacity = self._step_runtime_opacity(current, target)
                state['opacity'] = next_opacity
                overlay.set_opacity(next_opacity)
                if next_opacity <= 0.001:
                    overlay.hide()
                elif widget.isVisible():
                    overlay.show()
            except RuntimeError:
                continue

    def _step_runtime_opacity(self, current: float, target: float) -> float:
        current = max(0.0, min(float(current), 1.0))
        target = max(0.0, min(float(target), 1.0))
        if abs(target - current) <= _RUNTIME_BORDER_FADE_STEP:
            return target
        if target > current:
            return min(1.0, current + _RUNTIME_BORDER_FADE_STEP)
        return max(0.0, current - _RUNTIME_BORDER_FADE_STEP)

    def _apply_runtime_widget_border_color(self, widget: QWidget, color: QColor, *, opacity: float = 1.0) -> None:
        base_text = str(self._runtime_native_border_widgets.get(widget, {}).get('base_border_color', '') or '')
        blended = self._blend_runtime_border_color(base_text, color, opacity)
        self._set_style_value(widget, 'border-color', blended.name(QColor.NameFormat.HexRgb))

    def _blend_runtime_border_color(self, base_color_text: str, rainbow_color: QColor, opacity: float) -> QColor:
        mix = max(0.0, min(float(opacity), 1.0))
        target = QColor(rainbow_color)
        target.setAlpha(255)
        if mix <= 0.0:
            base = to_qcolor(base_color_text)
            return base if base is not None else target
        if mix >= 1.0:
            return target

        base = to_qcolor(base_color_text)
        if base is None:
            return target

        return QColor(
            round(base.red() + (target.red() - base.red()) * mix),
            round(base.green() + (target.green() - base.green()) * mix),
            round(base.blue() + (target.blue() - base.blue()) * mix),
            255,
        )

    def _restore_runtime_widget_border(self, widget: QWidget) -> None:
        overrides = self._style_overrides.setdefault(widget, {})
        previous = self._runtime_native_border_widgets.get(widget, {}).get('previous_border_color_override')
        changed = False
        if previous is None:
            if 'border-color' in overrides:
                overrides.pop('border-color', None)
                changed = True
        else:
            if overrides.get('border-color') != previous:
                overrides['border-color'] = str(previous)
                changed = True
        if changed:
            self._apply_widget_style(widget)

    def _detect_runtime_border_config(self, widget: QWidget) -> dict[str, float | bool | str]:
        declarations = self._collect_widget_declarations(widget)
        width_text = declarations.get('border-width')
        style_text = declarations.get('border-style')
        color_text = declarations.get('border-color')
        if (shorthand := declarations.get('border')):
            short_width, short_style, short_color = self._parse_border_shorthand(shorthand)
            width_text = width_text or short_width
            style_text = style_text or short_style
            color_text = color_text or short_color

        width = self._parse_measure_value(width_text)
        style = str(style_text or '').strip().lower()
        radius = self._parse_measure_value(declarations.get('border-radius'))
        if radius is None:
            radius = self._parse_measure_value(widget.property('_themeBorderRadius'))

        return {
            'visible': bool(width and width > 0.0 and style and style != 'none'),
            'width': max(1.0, float(width)) if width is not None else 1.5,
            'radius': max(0.0, float(radius)) if radius is not None else 0.0,
            'inset': max(0.5, (float(width) / 2.0)) if width is not None else 1.0,
            'color_text': str(color_text).strip() if isinstance(color_text, str) and color_text.strip() else '',
        }

    def _collect_widget_declarations(self, widget: QWidget) -> dict[str, str]:
        declarations: dict[str, str] = {}
        for raw in (
            widget.property('_themeBorderRule'),
            widget.property('_themeBorderRadius'),
            widget.styleSheet(),
        ):
            if isinstance(raw, str) and raw.strip():
                declarations.update(self._extract_css_declarations(raw))
        return declarations

    def _extract_css_declarations(self, text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for match in _CSS_DECLARATION_PATTERN.finditer(text):
            key = str(match.group(1)).strip().lower()
            value = str(match.group(2)).strip()
            if key and value:
                result[key] = value
        return result

    def _parse_border_shorthand(self, value: str) -> tuple[str | None, str | None, str | None]:
        text = str(value).strip()
        if not text:
            return None, None, None
        match = re.match(r'^(\S+)\s+(\S+)\s+(.+)$', text)
        if not match:
            return None, None, None
        width = str(match.group(1)).strip()
        style = str(match.group(2)).strip()
        color = str(match.group(3)).strip()
        return width or None, style or None, color or None

    def _parse_measure_value(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None
        text = value.strip().lower()
        if not text:
            return None
        if text.endswith('%'):
            return None
        if text.endswith('px'):
            text = text[:-2].strip()
        try:
            return float(text)
        except ValueError:
            return None

    def _ensure_dash_overlay(self, widget: QWidget, config: dict[str, Any]) -> DashBorderOverlay:
        overlay = self._paint_overlays.get(widget)
        if overlay is None:
            overlay = DashBorderOverlay(widget)
            self._paint_overlays[widget] = overlay

        overlay.configure(
            color=config['color'],
            width=config['width'],
            radius=config['radius'],
            dash_pattern=config['dash_pattern'],
            inset=config['inset'],
            pen_style=config['pen_style'],
            opacity=config.get('opacity', 1.0),
        )
        self._sync_paint_overlay_geometry(widget)
        return overlay

    def _ensure_gradient_overlay(self, widget: QWidget, config: dict[str, Any]) -> DashBorderOverlay:
        overlay = self._paint_overlays.get(widget)
        if overlay is None:
            overlay = DashBorderOverlay(widget)
            self._paint_overlays[widget] = overlay

        overlay.configure_gradient(
            width=config['width'],
            radius=config['radius'],
            inset=config['inset'],
            direction=config['direction'],
            stops=config['stops'],
            pen_style=config['pen_style'],
            dash_pattern=config['dash_pattern'],
            opacity=config.get('opacity', 1.0),
        )
        self._sync_paint_overlay_geometry(widget)
        return overlay

    def _dash_border_style_defaults(self, styles: dict[str, Any]) -> dict[str, Any] | None:
        raw: Any = None
        paint = theme_map(styles.get('paint'))
        if paint is not None:
            raw = paint.get('dash_border') or paint.get('dashBorder') or paint.get('border')
        if raw is None:
            raw = styles.get('dash_border') or styles.get('paint_dash_border')
        if raw is None:
            return None
        normalized = normalize_dash_border(raw)
        return normalized if isinstance(normalized, dict) else None

    def _merge_dash_border_style_defaults(self, effect: dict[str, Any], styles: dict[str, Any]) -> dict[str, Any]:
        defaults = self._dash_border_style_defaults(styles)
        if not defaults:
            return effect

        merged = deepcopy(effect)
        provided = set(merged.get('_provided', set()))

        for key in ('offset', 'phase_offset', 'phase_duration', 'opacity', 'brightness', 'saturation', 'width', 'radius', 'inset', 'dash_pattern', 'pen_style', 'seamless'):
            if key not in provided and key in defaults:
                merged[key] = deepcopy(defaults[key])

        if 'color' not in provided:
            if 'color' in defaults:
                merged['color'] = QColor(defaults['color'])
            if 'shared_color' in defaults:
                merged['shared_color'] = bool(defaults['shared_color'])

        return merged

    def _style_handle_rainbow_duration(self, styles: dict[str, Any]) -> int | None:
        parts = theme_map(styles.get('parts')) or {}
        handle = theme_map(parts.get('handle')) or {}
        rainbow = theme_map(handle.get('rainbow')) or {}
        value = rainbow.get('phase_duration', rainbow.get('rainbow_duration', rainbow.get('period')))
        duration_value = coerce_float(value)
        if duration_value is None:
            return None
        return max(1, int(round(duration_value)))

    def _rainbow_animation_duration(self, spec: AnimationSpec, styles: dict[str, Any]) -> int:
        if spec.property_key != 'parts.handle.rainbow':
            return spec.duration
        options = spec.options if isinstance(spec.options, dict) else {}
        if bool(options.get('duration_provided')):
            return spec.duration
        return self._style_handle_rainbow_duration(styles) or spec.duration

    def _append_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        base_styles: dict[str, Any],
    ) -> None:
        runtime: dict[str, Any] = {}
        self._remember_action_property(widget, spec)

        match spec.kind:
            case 'color':
                self._append_color_animation(widget, spec, group, base_styles, runtime)
                return

            case 'gradient':
                self._append_gradient_animation(widget, spec, group, base_styles, runtime)
                return

            case 'number':
                self._append_number_animation(widget, spec, group, runtime)
                return

            case 'paint_dash_border':
                self._append_dash_border_animation(widget, spec, group, base_styles, runtime)
                return

            case 'paint_gradient_border':
                self._append_gradient_border_animation(widget, spec, group, runtime)
                return
            case _:
                return

    def _append_color_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        base_styles: dict[str, Any],
        runtime: dict[str, Any],
    ) -> None:
        if self._append_runtime_border_color_animation(widget, spec, group, base_styles, runtime):
            return

        def on_start() -> None:
            cache = self._cache.setdefault(widget, {})
            start_color = self._animation_start_color(widget, spec, base_styles, cache)
            runtime['start'] = QColor(start_color)

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            start_color = runtime.get('start', spec.end)
            color = interpolate_color(start_color, spec.end, t)
            self._set_style_value(widget, spec.css_property, normalize_color(color) or color.name(), source_action=spec.action)
            self._cache[widget][spec.property_key] = QColor(color)

        animation = TimerAnimation(spec.duration, spec.easing, on_start, on_update, parent=widget)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)

    def _append_runtime_border_color_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        base_styles: dict[str, Any],
        runtime: dict[str, Any],
    ) -> bool:
        if spec.property_key != 'border.color':
            return False

        border_config = self._detect_runtime_border_config(widget)
        if not bool(border_config.get('visible')):
            return False

        border_state: dict[str, Any] = {'previous': None, 'captured': False}

        def capture_previous_border_override() -> None:
            if border_state['captured']:
                return
            border_state['previous'] = deepcopy(self._style_overrides.get(widget, {}).get('border-color'))
            border_state['captured'] = True

        def restore_previous_border_override() -> None:
            overrides = self._style_overrides.setdefault(widget, {})
            previous = border_state.get('previous')
            changed = False
            if previous is None:
                if 'border-color' in overrides:
                    overrides.pop('border-color', None)
                    changed = True
            elif overrides.get('border-color') != previous:
                overrides['border-color'] = str(previous)
                changed = True
            if changed:
                self._apply_widget_style(widget)

        def on_start() -> None:
            cache = self._cache.setdefault(widget, {})
            start_color = self._animation_start_color(widget, spec, base_styles, cache)
            runtime['start'] = QColor(start_color)
            capture_previous_border_override()
            effect = {
                'color': QColor(start_color),
                'width': float(border_config.get('width', 1.5)),
                'radius': float(border_config.get('radius', 10.0)),
                'dash_pattern': [9999.0, 1.0],
                'inset': 0.0,
                'pen_style': Qt.PenStyle.SolidLine,
                'opacity': max(0.0, min(QColor(start_color).alphaF(), 1.0)),
            }
            overlay = self._ensure_dash_overlay(widget, effect)
            runtime['overlay'] = overlay
            transparent = normalize_color(QColor(Qt.GlobalColor.transparent)) or 'transparent'
            self._set_style_value(widget, 'border-color', transparent, source_action=spec.action)
            if widget.isVisible() and overlay.opacity() > 0.0:
                overlay.show()

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            start_color = runtime.get('start', spec.end)
            color = interpolate_color(start_color, spec.end, t)
            overlay = runtime.get('overlay')
            if not isinstance(overlay, DashBorderOverlay):
                return
            opaque = QColor(color)
            opaque.setAlpha(255)
            overlay.set_color(opaque)
            overlay.set_opacity(color.alphaF())
            if widget.isVisible() and color.alphaF() > 0.0:
                self._sync_paint_overlay_geometry(widget)
                overlay.show()
            else:
                overlay.hide()
            self._cache[widget][spec.property_key] = QColor(color)

        def on_finished() -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            overlay = runtime.get('overlay')
            if not isinstance(overlay, DashBorderOverlay):
                restore_previous_border_override()
                return
            if QColor(spec.end).alphaF() <= 0.001:
                overlay.hide()
                restore_previous_border_override()

        animation = TimerAnimation(spec.duration, spec.easing, on_start, on_update, parent=widget)
        animation.finished.connect(on_finished)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)
        return True

    def _append_gradient_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        base_styles: dict[str, Any],
        runtime: dict[str, Any],
    ) -> None:
        def on_start() -> None:
            cache = self._cache.setdefault(widget, {})
            start_grad: object = cache.get(spec.property_key) if spec.action in {'hover', 'leave'} else spec.start
            if start_grad is None:
                start_grad = spec.start if spec.action in {'hover', 'leave'} else cache.get(spec.property_key)
            if not isinstance(start_grad, dict):
                start_grad = self._sample_style_gradient(base_styles, spec.property_key, fallback=spec.end)
            if not isinstance(start_grad, dict) and spec.property_key.startswith('parts.'):
                tokens = spec.property_key.split('.')
                if len(tokens) == 4 and tokens[2] == 'background' and tokens[3] == 'gradient':
                    if isinstance(widget, (MTSlider, MTSwitch, MTComboBox)):
                        start_grad = theme_map(widget.current_part_gradient(tokens[1]))
            start_grad_map = theme_map(cast(object, start_grad))
            if start_grad_map is None:
                end_map = theme_map(spec.end)
                if end_map is None:
                    return
                start_grad_map = clone_gradient(end_map)
            runtime['start'] = clone_gradient(start_grad_map)

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            start_grad = runtime.get('start', spec.end)
            grad = interpolate_gradient(start_grad, spec.end, t)
            if self._apply_runtime_part_gradient(widget, spec, grad):
                self._cache[widget][spec.property_key] = clone_gradient(grad)
                return
            self._set_style_value(widget, spec.css_property, gradient_to_qss(grad), source_action=spec.action)
            self._cache[widget][spec.property_key] = clone_gradient(grad)

        animation = TimerAnimation(spec.duration, spec.easing, on_start, on_update, parent=widget)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)

    def _apply_runtime_part_gradient(self, widget: QWidget, spec: AnimationSpec, gradient: dict[str, Any]) -> bool:
        if not spec.property_key.startswith('parts.'):
            return False
        tokens = spec.property_key.split('.')
        if len(tokens) != 4 or tokens[2] != 'background' or tokens[3] != 'gradient':
            return False
        if isinstance(widget, (MTSlider, MTSwitch, MTComboBox)):
            return bool(widget.set_part_gradient(tokens[1], gradient))
        return False

    def _append_number_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        runtime: dict[str, Any],
    ) -> None:
        def on_start() -> None:
            self._notify_part_animation_state(widget, spec.property_key, True)
            cache = self._cache.setdefault(widget, {})
            start_value = spec.start
            if start_value is None:
                start_value = cache.get(spec.property_key)
            if not isinstance(start_value, (int, float)):
                start_value = self._sample_number(widget, spec.property_key, fallback=float(spec.end))
            start_value = float(start_value)
            runtime['start'] = start_value
            if spec.action == 'wheel' and spec.property_key in {'scroll.vertical', 'scroll.horizontal'}:
                runtime['delta'] = self._resolve_wheel_scroll_delta(widget, spec)
                runtime['end'] = start_value + float(runtime['delta'])
            else:
                end_value = self._normalize_number_target(widget, spec.property_key, float(spec.end))
                runtime['end'] = end_value
                runtime['delta'] = end_value - start_value

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            start_value = float(runtime.get('start', spec.end))
            delta = float(runtime.get('delta', spec.end))
            value = start_value + (delta * t)
            self._set_number_property(widget, spec.property_key, value)
            actual_value = self._sample_number(widget, spec.property_key, fallback=float(value))
            self._cache[widget][spec.property_key] = float(actual_value)

        animation = TimerAnimation(
            spec.duration,
            spec.easing,
            on_start,
            on_update,
            parent=widget,
            restart_each_loop=False,
        )

        def on_finished() -> None:
            self._notify_part_animation_state(widget, spec.property_key, False)

        animation.finished.connect(on_finished)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)

    def _append_dash_border_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        base_styles: dict[str, Any],
        runtime: dict[str, Any],
    ) -> None:
        effect_map = theme_map(spec.end)
        if effect_map is None:
            return

        effect = self._merge_dash_border_style_defaults(effect_map, base_styles)
        self._paint_border_profiles[widget] = deepcopy(effect)
        overlay = self._ensure_dash_overlay(widget, effect)

        def on_start() -> None:
            cache = self._cache.setdefault(widget, {})
            start_offset = spec.start
            if start_offset is None:
                start_offset = cache.get(spec.property_key, overlay.gradient_phase())
            start_offset = float(start_offset)
            end_offset = float(effect.get('offset', 0.0))

            start_opacity = cache.get(f'{spec.property_key}.opacity', overlay.opacity())
            try:
                start_opacity = float(start_opacity)
            except (TypeError, ValueError):
                start_opacity = overlay.opacity()
            end_opacity = float(effect.get('opacity', 1.0))

            if spec.loop_count != 1 and bool(effect.get('seamless', True)):
                period = sum(float(v) for v in effect.get('dash_pattern', []))
                if period > 0.0:
                    delta = end_offset - start_offset
                    direction = 1.0 if delta >= 0.0 else -1.0
                    turns = max(1, int(math.ceil(abs(delta) / period)))
                    end_offset = start_offset + (direction * period * turns)

            runtime['start'] = start_offset
            runtime['end'] = end_offset
            runtime['start_opacity'] = max(0.0, min(start_opacity, 1.0))
            runtime['end_opacity'] = max(0.0, min(end_opacity, 1.0))
            self._ensure_dash_overlay(widget, effect)
            if bool(effect.get('shared_color')):
                self._set_shared_border_color_active(
                    overlay,
                    effect.get('phase_duration', 5000.0),
                    effect.get('phase_offset', 0.0),
                    True,
                    brightness=effect.get('brightness', 1.0),
                    saturation=effect.get('saturation', 1.0),
                )
            else:
                self._set_shared_border_color_active(overlay, 0, 0.0, False)
            if widget.isVisible():
                overlay.show()

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            start_opacity = float(runtime.get('start_opacity', overlay.opacity()))
            end_opacity = float(runtime.get('end_opacity', effect.get('opacity', 1.0)))
            opacity = start_opacity + ((end_opacity - start_opacity) * t)
            overlay.set_opacity(opacity)
            self._cache[widget][f'{spec.property_key}.opacity'] = float(opacity)

            start_offset = float(runtime.get('start', 0.0))
            end_offset = float(runtime.get('end', effect.get('offset', 0.0)))
            offset = start_offset + (end_offset - start_offset) * t
            overlay.set_dash_offset(offset)
            if widget.isVisible() and not overlay.isVisible() and opacity > 0.0:
                self._sync_paint_overlay_geometry(widget)
                overlay.show()
            self._cache[widget][spec.property_key] = float(offset)

        def on_finished() -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            end_opacity = float(runtime.get('end_opacity', effect.get('opacity', 1.0)))
            if end_opacity <= 0.0:
                self._set_shared_border_color_active(overlay, 0, 0.0, False)
                overlay.hide()

        animation = TimerAnimation(spec.duration, spec.easing, on_start, on_update, parent=widget)
        animation.finished.connect(on_finished)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)

    def _append_gradient_border_animation(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        group: QParallelAnimationGroup,
        runtime: dict[str, Any],
    ) -> None:
        end_map = theme_map(spec.end)
        if end_map is None:
            return

        overlay = self._ensure_gradient_overlay(widget, end_map)

        def on_start() -> None:
            cache = self._cache.setdefault(widget, {})
            shared_phase = bool(end_map.get('shared_phase'))
            start_phase = spec.start
            if start_phase is None:
                start_phase = cache.get(spec.property_key, overlay.gradient_phase())
            start_phase = float(start_phase)
            end_phase = float(end_map.get('phase', 1.0))

            start_opacity = cache.get(f'{spec.property_key}.opacity', overlay.opacity())
            try:
                start_opacity = float(start_opacity)
            except (TypeError, ValueError):
                start_opacity = overlay.opacity()
            end_opacity = float(end_map.get('opacity', 1.0))

            if not shared_phase and spec.loop_count != 1 and bool(end_map.get('seamless', True)):
                delta = end_phase - start_phase
                direction = 1.0 if delta >= 0.0 else -1.0
                turns = max(1, int(math.ceil(abs(delta)))) if abs(delta) > 1e-6 else 1
                end_phase = start_phase + (direction * turns)

            runtime['start'] = start_phase
            runtime['end'] = end_phase
            runtime['start_opacity'] = max(0.0, min(start_opacity, 1.0))
            runtime['end_opacity'] = max(0.0, min(end_opacity, 1.0))
            self._ensure_gradient_overlay(widget, end_map)
            if shared_phase:
                self._set_shared_gradient_border_active(
                    overlay,
                    end_map.get('phase_duration', 5000.0),
                    end_map.get('phase_offset', 0.0),
                    True,
                )
            else:
                self._set_shared_gradient_border_active(overlay, 0, 0.0, False)
            if widget.isVisible():
                overlay.show()

        def on_update(t: float) -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            shared_phase = bool(end_map.get('shared_phase'))
            start_opacity = float(runtime.get('start_opacity', overlay.opacity()))
            end_opacity = float(runtime.get('end_opacity', end_map.get('opacity', 1.0)))
            opacity = start_opacity + ((end_opacity - start_opacity) * t)
            overlay.set_opacity(opacity)
            self._cache[widget][f'{spec.property_key}.opacity'] = float(opacity)

            if not shared_phase:
                start_phase = float(runtime.get('start', 0.0))
                end_phase = float(runtime.get('end', end_map.get('phase', 1.0)))
                phase = start_phase + (end_phase - start_phase) * t
                overlay.set_gradient_phase(phase)
                self._cache[widget][spec.property_key] = float(phase)

            if widget.isVisible() and not overlay.isVisible() and opacity > 0.0:
                self._sync_paint_overlay_geometry(widget)
                overlay.show()

        def on_finished() -> None:
            if not self._is_spec_action_active(widget, spec):
                return
            end_opacity = float(runtime.get('end_opacity', end_map.get('opacity', 1.0)))
            if end_opacity <= 0.0:
                self._set_shared_gradient_border_active(overlay, 0, 0.0, False)
                overlay.hide()

        animation = TimerAnimation(spec.duration, spec.easing, on_start, on_update, parent=widget)
        animation.finished.connect(on_finished)
        animation.setLoopCount(spec.loop_count)
        group.addAnimation(animation)

    def _play(self, widget: QWidget, action: str) -> None:
        groups = self._animations.get(widget)
        if not groups:
            return

        if action in {'hover', 'leave'} and self._play_checkable_state(widget):
            return

        group = groups.get(action)
        if not group:
            return

        self._start_action_group(widget, action, group, groups)

    def _handle_wheel_event(self, widget: QWidget, event: QWheelEvent) -> bool:
        groups = self._animations.get(widget)
        if not groups:
            return False

        group = groups.get('wheel')
        if group is None:
            return False

        angle_delta = event.angleDelta()
        pixel_delta = event.pixelDelta()
        vertical_delta = float(angle_delta.y())
        horizontal_delta = float(angle_delta.x())
        if abs(vertical_delta) < 0.001 and abs(horizontal_delta) < 0.001:
            vertical_delta = float(pixel_delta.y())
            horizontal_delta = float(pixel_delta.x())

        if abs(vertical_delta) < 0.001 and abs(horizontal_delta) < 0.001:
            return False

        self._wheel_event_deltas[widget] = {
            'vertical': vertical_delta,
            'horizontal': horizontal_delta,
        }
        self._start_action_group(widget, 'wheel', group, groups, force=True, restart_running=True)
        return True

    def _start_action_group(
        self,
        widget: QWidget,
        action: str,
        group: QParallelAnimationGroup,
        groups: dict[str, QParallelAnimationGroup],
        *,
        force: bool = False,
        restart_running: bool = False,
    ) -> None:
        if not force and self._action_properties_are_active(widget, action):
            has_running_conflict = any(
                group_name not in {'always', action} and
                running_group.state() == QAbstractAnimation.State.Running
                for group_name, running_group in groups.items()
            )
            specs = self._action_specs.get(widget, {}).get(action, [])
            if not has_running_conflict and specs and all(
                self._spec_final_state_matches(widget, spec) for spec in specs
            ):
                return

        self._activate_action_properties(widget, action)
        for group_name, running_group in groups.items():
            if group_name in {'always', action}:
                continue
            if running_group.state() == QAbstractAnimation.State.Running:
                running_group.stop()

        if restart_running and group.state() == QAbstractAnimation.State.Running:
            group.stop()

        if group.state() == QAbstractAnimation.State.Running:
            return

        group.start()
        if action in {'hover', 'leave'}:
            self._start_hover_reconcile_timer()

    def _play_checkable_state(self, widget: QWidget, *, force: bool = False) -> bool:
        groups = self._animations.get(widget)
        if not groups:
            return False

        action = self._resolve_checkable_state_action(widget, groups)
        if action is None:
            return False

        group = groups.get(action)
        if group is None:
            return False

        self._start_action_group(widget, action, group, groups, force=force)
        return True

    def _resolve_checkable_state_action(self, widget: QWidget, groups: dict[str, QParallelAnimationGroup]) -> str | None:
        if not isinstance(widget, QAbstractButton):
            return None
        if not widget.isCheckable():
            return None

        if widget.isChecked() and 'checked' in groups:
            return 'checked'

        if widget in self._hovered_widgets and 'hover' in groups:
            return 'hover'

        if 'unchecked' in groups:
            return 'unchecked'
        if 'leave' in groups:
            return 'leave'
        return None

    def _remember_action_property(self, widget: QWidget, spec: AnimationSpec) -> None:
        self._action_property_keys.setdefault(widget, {}).setdefault(spec.action, set()).add(spec.property_key)
        self._action_specs.setdefault(widget, {}).setdefault(spec.action, []).append(spec)

    def _activate_action_properties(self, widget: QWidget, action: str) -> None:
        property_keys = self._action_property_keys.get(widget, {}).get(action)
        if not property_keys:
            return

        active = self._active_property_actions.setdefault(widget, {})
        for property_key in property_keys:
            active[property_key] = action

    def _action_properties_are_active(self, widget: QWidget, action: str) -> bool:
        property_keys = self._action_property_keys.get(widget, {}).get(action)
        if not property_keys:
            return False

        active = self._active_property_actions.get(widget, {})
        return all(active.get(property_key) == action for property_key in property_keys)

    def _is_spec_action_active(self, widget: QWidget, spec: AnimationSpec) -> bool:
        if spec.action == 'always':
            return True

        if spec.action == 'hover' and not self._cursor_over_widget(widget):
            self._hovered_widgets.discard(widget)
            self._queue_hover_exit(widget)
            return False

        active_action = self._active_property_actions.get(widget, {}).get(spec.property_key)
        if active_action is None or active_action == spec.action:
            return True
        return self._actions_have_same_end_value(widget, active_action, spec.action, spec.property_key)

    def _has_running_equivalent_action(
        self,
        widget: QWidget,
        action: str,
        groups: dict[str, QParallelAnimationGroup],
    ) -> bool:
        for group_name, running_group in groups.items():
            if group_name in {'always', action}:
                continue
            if running_group.state() != QAbstractAnimation.State.Running:
                continue
            if self._actions_are_equivalent(widget, action, group_name):
                return True
        return False

    def _actions_are_equivalent(self, widget: QWidget, left: str, right: str) -> bool:
        left_specs = self._action_specs.get(widget, {}).get(left, [])
        right_specs = self._action_specs.get(widget, {}).get(right, [])
        if not left_specs or not right_specs:
            return False

        right_keys = {spec.property_key for spec in right_specs}
        left_keys = {spec.property_key for spec in left_specs}
        if left_keys != right_keys:
            return False

        return all(
            self._actions_have_same_end_value(widget, left, right, property_key)
            for property_key in left_keys
        )

    def _actions_have_same_end_value(self, widget: QWidget, left: str, right: str, property_key: str) -> bool:
        left_spec = self._action_spec_for_property(widget, left, property_key)
        right_spec = self._action_spec_for_property(widget, right, property_key)
        if left_spec is None or right_spec is None:
            return False
        return self._animation_end_signature(left_spec) == self._animation_end_signature(right_spec)

    def _action_spec_for_property(self, widget: QWidget, action: str, property_key: str) -> AnimationSpec | None:
        for spec in self._action_specs.get(widget, {}).get(action, []):
            if spec.property_key == property_key:
                return spec
        return None

    def _animation_end_signature(self, spec: AnimationSpec) -> tuple[str, Any]:
        if spec.kind == 'color':
            color = to_qcolor(spec.end)
            if color is not None:
                return spec.kind, color.name(QColor.NameFormat.HexArgb)
        if spec.kind == 'number':
            try:
                return spec.kind, float(spec.end)
            except (TypeError, ValueError):
                pass
        return spec.kind, repr(spec.end)

    def _normalize_number_target(self, widget: QWidget, property_key: str, value: float) -> float:
        if property_key.startswith('parts.'):
            tokens = property_key.split('.')
            if isinstance(widget, MTCollapsibleContainer) and len(tokens) >= 3:
                try:
                    normalized = widget.normalize_part_metric(tokens[1], tuple(tokens[2:]), float(value))
                except (RuntimeError, TypeError, ValueError):
                    return float(value)
                return coerce_float(normalized, float(value)) or float(value)
        return float(value)

    def _notify_part_animation_state(self, widget: QWidget, property_key: str, active: bool) -> None:
        if not property_key.startswith('parts.'):
            return
        tokens = property_key.split('.')
        if len(tokens) < 3:
            return
        if not isinstance(widget, MTCollapsibleContainer):
            return
        try:
            widget.handle_part_animation_state(tokens[1], tuple(tokens[2:]), bool(active))
        except RuntimeError:
            return

    def _queue_checkable_reconcile(self, widget: QWidget) -> None:
        if widget in self._pending_checkable_reconcile_widgets:
            return

        if not isinstance(widget, QAbstractButton) or not widget.isCheckable():
            return
        if widget not in self._animations:
            return

        self._pending_checkable_reconcile_widgets.add(widget)

        def reconcile_checkable() -> None:
            self._reconcile_checkable_state(widget)

        QTimer.singleShot(0, reconcile_checkable)

    def _queue_hover_exit(self, widget: QWidget) -> None:
        if widget in self._pending_hover_exit_widgets:
            return
        if widget not in self._animations:
            return

        self._pending_hover_exit_widgets.add(widget)

        def reconcile_hover() -> None:
            self._reconcile_hover_exit(widget)

        QTimer.singleShot(0, reconcile_hover)

    def _reconcile_hover_exit(self, widget: QWidget) -> None:
        self._pending_hover_exit_widgets.discard(widget)
        if widget not in self._animations:
            return
        if self._cursor_over_widget(widget):
            self._hovered_widgets.add(widget)
            return

        self._hovered_widgets.discard(widget)
        if not self._play_checkable_state(widget, force=True):
            self._play(widget, 'leave')
        self._start_hover_reconcile_timer()

    def _start_hover_reconcile_timer(self) -> None:
        if not self._hover_reconcile_timer.isActive():
            self._hover_reconcile_timer.start()

    def _reconcile_hover_states(self) -> None:
        should_continue = False
        widgets = (
            set(self._animations)
            | set(self._runtime_native_border_widgets)
            | set(self._runtime_hover_overlays)
        )

        for widget in list(widgets):
            try:
                is_over = self._cursor_over_widget(widget)
            except RuntimeError:
                self._hovered_widgets.discard(widget)
                continue

            if is_over and widget not in self._hovered_widgets:
                self._hovered_widgets.add(widget)
                if widget in self._animations:
                    self._play(widget, 'hover')
            elif not is_over and widget in self._hovered_widgets:
                self._hovered_widgets.discard(widget)
                if widget in self._animations and not self._play_checkable_state(widget, force=True):
                    self._play(widget, 'leave')

            groups = self._animations.get(widget, {})
            if any(
                name in {'hover', 'leave'} and group.state() == QAbstractAnimation.State.Running
                for name, group in groups.items()
            ):
                should_continue = True

        if should_continue:
            return
        self._hover_reconcile_timer.stop()

    def _cursor_over_widget(self, widget: QWidget) -> bool:
        try:
            if not widget.isVisible():
                return False
            cursor_pos = QCursor.pos()
            local_pos = widget.mapFromGlobal(cursor_pos)
            if not widget.rect().contains(local_pos):
                return False

            top_widget = QApplication.widgetAt(cursor_pos)
            if top_widget is None:
                return False

            current: QWidget | None = top_widget
            while current is not None:
                if current is widget:
                    return True
                current = current.parentWidget()
            return False
        except RuntimeError:
            return False

    def _reconcile_checkable_state(self, widget: QWidget) -> None:
        self._pending_checkable_reconcile_widgets.discard(widget)
        groups = self._animations.get(widget)
        if not groups:
            return

        action = self._resolve_checkable_state_action(widget, groups)
        if action is None:
            return

        if self._action_properties_are_active(widget, action):
            group = groups.get(action)
            if group is not None and group.state() == QAbstractAnimation.State.Running:
                return
            if self._has_running_equivalent_action(widget, action, groups):
                return
            specs = self._action_specs.get(widget, {}).get(action, [])
            if specs and all(self._spec_final_state_matches(widget, spec) for spec in specs):
                return
            if group is not None:
                self._start_action_group(widget, action, group, groups, force=True)
                return
            self._apply_action_final_state(widget, action)
            return

        group = groups.get(action)
        if group is not None:
            self._start_action_group(widget, action, group, groups)

    def _animation_start_color(
        self,
        widget: QWidget,
        spec: AnimationSpec,
        base_styles: dict[str, Any],
        cache: dict[str, Any],
    ) -> QColor:
        candidates: list[Any]
        if spec.action in {'hover', 'leave'}:
            candidates = [
                self._sample_override_color(widget, spec.css_property),
                cache.get(spec.property_key),
                self._sample_style_color(base_styles, spec.property_key),
                self._sample_color(widget, spec.css_property, fallback=spec.end),
                spec.start,
            ]
        else:
            candidates = [
                spec.start,
                cache.get(spec.property_key),
                self._sample_override_color(widget, spec.css_property),
                self._sample_style_color(base_styles, spec.property_key),
                self._sample_color(widget, spec.css_property, fallback=spec.end),
            ]

        for candidate in candidates:
            if isinstance(candidate, QColor):
                return QColor(candidate)
            color = to_qcolor(candidate)
            if color is not None:
                return QColor(color)

        return QColor(spec.end)

    def _apply_action_final_state(self, widget: QWidget, action: str) -> None:
        specs = self._action_specs.get(widget, {}).get(action, [])
        if not specs:
            return

        self._activate_action_properties(widget, action)
        for spec in specs:
            match spec.kind:
                case 'color':
                    value = normalize_color(spec.end) or QColor(spec.end).name()
                    self._set_style_value(widget, spec.css_property, value, source_action=action)
                    self._cache.setdefault(widget, {})[spec.property_key] = QColor(spec.end)
                case 'gradient':
                    end_map = theme_map(spec.end)
                    if end_map is None:
                        continue
                    if self._apply_part_gradient_final_state(widget, spec.property_key, end_map):
                        self._cache.setdefault(widget, {})[spec.property_key] = clone_gradient(end_map)
                        continue
                    self._set_style_value(widget, spec.css_property, gradient_to_qss(end_map), source_action=action)
                    self._cache.setdefault(widget, {})[spec.property_key] = clone_gradient(end_map)
                case 'number':
                    target_value = self._normalize_number_target(widget, spec.property_key, float(spec.end))
                    self._set_number_property(widget, spec.property_key, target_value)
                    self._cache.setdefault(widget, {})[spec.property_key] = float(target_value)
                case _:
                    continue

    def _apply_part_gradient_final_state(self, widget: QWidget, property_key: str, gradient: dict[str, Any]) -> bool:
        if not property_key.startswith('parts.'):
            return False
        tokens = property_key.split('.')
        if len(tokens) != 4 or tokens[2] != 'background' or tokens[3] != 'gradient':
            return False
        if isinstance(widget, (MTSlider, MTSwitch, MTComboBox)):
            return bool(widget.set_part_gradient(tokens[1], gradient))
        return False

    def _spec_final_state_matches(self, widget: QWidget, spec: AnimationSpec) -> bool:
        match spec.kind:
            case 'color':
                expected = to_qcolor(spec.end)
                if expected is None:
                    return False
                current = self._sample_override_color(widget, spec.css_property)
                if current is None:
                    cached = self._cache.get(widget, {}).get(spec.property_key)
                    current = QColor(cached) if isinstance(cached, QColor) else None
                return current is not None and self._colors_are_close(current, expected)
            case 'number':
                try:
                    expected = self._normalize_number_target(widget, spec.property_key, float(spec.end))
                    current = self._sample_number(widget, spec.property_key, fallback=float(expected))
                    return abs(float(current) - float(expected)) <= 0.5
                except (TypeError, ValueError):
                    return False
            case _:
                return False
        return False

    def _colors_are_close(self, left: QColor, right: QColor) -> bool:
        return (
            abs(left.red() - right.red()) <= 1 and
            abs(left.green() - right.green()) <= 1 and
            abs(left.blue() - right.blue()) <= 1 and
            abs(left.alpha() - right.alpha()) <= 1
        )

    def _set_style_value(self, widget: QWidget, css_property: str, value: str, *, source_action: str | None = None) -> None:
        if self._set_direct_widget_style_value(widget, css_property, value):
            return

        if self._should_defer_locked_tab_style(widget, source_action):
            return

        if self._update_style_override_value(widget, css_property, value):
            self._apply_widget_style(widget)

    def _set_direct_widget_style_value(self, widget: QWidget, css_property: str, value: str) -> bool:
        if css_property.startswith('slider.'):
            self._set_slider_style_value(widget, css_property, value)
            return True
        if css_property.startswith('parts.'):
            return self._set_parts_style_value(widget, css_property, value)
        if self._set_box_style_value(widget, css_property, value):
            return True
        return self._set_text_style_value(widget, css_property, value)

    def _should_defer_locked_tab_style(self, widget: QWidget, source_action: str | None) -> bool:
        if self._is_locked_tab(widget) and source_action != 'checked':
            self._locked_tabs.add(widget)
            return True
        self._locked_tabs.discard(widget)
        return False

    def _update_style_override_value(self, widget: QWidget, css_property: str, value: str) -> bool:
        border_related_property = css_property == 'border' or css_property == 'border-color' or css_property.startswith('border-')
        if border_related_property and bool(widget.property('_rainbowRuntimeBorderTarget')):
            return False

        overrides = self._style_overrides.setdefault(widget, {})
        changed = self._clear_conflicting_style_override(overrides, css_property)
        if overrides.get(css_property) != value:
            overrides[css_property] = value
            changed = True
        return changed

    def _clear_conflicting_style_override(self, overrides: dict[str, str], css_property: str) -> bool:
        changed = False
        match css_property:
            case 'background':
                if 'background-color' in overrides:
                    overrides.pop('background-color', None)
                    changed = True
            case 'background-color':
                if 'background' in overrides:
                    overrides.pop('background', None)
                    changed = True
            case 'border':
                if 'border-color' in overrides:
                    overrides.pop('border-color', None)
                    changed = True
            case 'border-color':
                if 'border' in overrides:
                    overrides.pop('border', None)
                    changed = True
            case _:
                pass
        return changed

    def _set_box_style_value(self, widget: QWidget, css_property: str, value: str) -> bool:
        if not isinstance(widget, BoxThemeMixin) or not isinstance(widget.box_theme_state(), dict):
            return False

        if css_property in {'background', 'background-color'}:
            return bool(widget.set_box_background_color(value))

        if css_property == 'border-color':
            return bool(widget.set_box_border_color(value))

        if css_property == 'border-width':
            return bool(widget.set_box_border(width=value))

        if css_property == 'border-radius':
            return bool(widget.set_box_border(radius=value))

        return False

    def _set_text_style_value(self, widget: QWidget, css_property: str, value: str) -> bool:
        _ = (widget, css_property, value)
        return False

    def _set_parts_style_value(self, widget: QWidget, css_property: str, value: str) -> bool:
        if self._is_runtime_handle_rainbow_active(widget, css_property):
            return True

        direct_setter = widget.set_part_style_value if isinstance(widget, (MTSlider, MTSwitch, MTComboBox)) else None

        direct_parts = css_property.split('.', 2)
        if len(direct_parts) == 3 and direct_parts[0] == 'parts' and direct_setter is not None:
            _, part, css_name = direct_parts
            if css_name.startswith('states.'):
                chunks = css_name.split('.')
                if len(chunks) == 3 and chunks[0] == 'states':
                    prefix = ('states', chunks[1])
                    nested_path = {
                        'background-color': (*prefix, 'background', 'color'),
                        'background': (*prefix, 'background', 'gradient'),
                        'color': (*prefix, 'text', 'color'),
                        'border-color': (*prefix, 'border', 'color'),
                    }.get(chunks[2])
                    if nested_path is not None:
                        return bool(direct_setter(part, nested_path, value))
            elif css_name in {'color', 'background-color', 'border-color'}:
                color_path = {
                    'color': ('color',),
                    'background-color': ('background', 'color'),
                    'border-color': ('border', 'color'),
                }.get(css_name)
                if color_path is not None and direct_setter(part, color_path, value):
                    return True

        mapped = self._map_parts_css_property(widget, css_property)
        if mapped.startswith('slider.'):
            self._set_slider_style_value(widget, mapped, value)
            return True

        mapped_parts = mapped.split('.', 2)
        if len(mapped_parts) != 3 or direct_setter is None:
            return False

        _, part, css_name = mapped_parts
        if css_name.startswith('states.'):
            chunks = css_name.split('.')
            if len(chunks) != 3 or chunks[0] != 'states':
                return False
            prefix = ('states', chunks[1])
            nested_path = {
                'background-color': (*prefix, 'background', 'color'),
                'background': (*prefix, 'background', 'gradient'),
                'color': (*prefix, 'text', 'color'),
                'border-color': (*prefix, 'border', 'color'),
            }.get(chunks[2])
            return bool(nested_path and direct_setter(part, nested_path, value))
        if css_name in {'color', 'background-color', 'border-color'}:
            color_path = {
                'color': ('color',),
                'background-color': ('background', 'color'),
                'border-color': ('border', 'color'),
            }.get(css_name)
            return bool(color_path and direct_setter(part, color_path, value))
        return False

    def _is_runtime_handle_rainbow_active(self, widget: QWidget, css_property: str) -> bool:
        if not css_property.startswith('parts.handle.'):
            return False

        css_name = css_property.rsplit('.', 1)[-1]
        if css_name not in {'color', 'background-color'}:
            return False

        if not isinstance(widget, MTSwitch):
            return False

        try:
            value = widget.current_handle_rainbow()
        except RuntimeError:
            return False
        return (coerce_float(value, 0.0) or 0.0) > 0.0

    def _map_parts_css_property(self, widget: QWidget, css_property: str) -> str:
        if not css_property.startswith('parts.'):
            return css_property

        parts = css_property.split('.', 2)
        if len(parts) != 3:
            return css_property

        _, part, css_name = parts
        if isinstance(widget, QSlider) and part in {'groove', 'sub_page', 'add_page', 'handle'}:
            slider_part = 'sub-page' if part == 'sub_page' else 'add-page' if part == 'add_page' else part
            return f'slider.{slider_part}.{css_name}'
        return css_property

    def _set_slider_style_value(self, widget: QWidget, css_property: str, value: str) -> None:
        parts = css_property.split('.', 2)
        if len(parts) != 3:
            return

        _, part, css_name = parts
        overrides = self._slider_style_overrides.setdefault(widget, {})
        part_overrides = overrides.setdefault(part, {})
        if part_overrides.get(css_name) == value:
            return

        part_overrides[css_name] = value
        self._apply_widget_style(widget)

    def _apply_widget_style(self, widget: QWidget) -> None:
        base_style = self._base_styles.get(widget, '')
        blocks = self._widget_style_blocks(widget)
        if not blocks:
            self._reset_widget_style(widget, base_style)
            return

        self._apply_managed_widget_style(widget, base_style, blocks)

    def _widget_style_blocks(self, widget: QWidget) -> list[str]:
        blocks: list[str] = []
        if override_block := self._widget_override_style_block(widget):
            blocks.append(override_block)
        slider_overrides = self._slider_style_overrides.get(widget, {})
        blocks.extend(self._build_slider_override_blocks(widget, slider_overrides))
        return blocks

    def _widget_override_style_block(self, widget: QWidget) -> str:
        overrides = self._style_overrides.get(widget, {})
        if not overrides:
            return ''

        effective_overrides = self._effective_style_overrides(widget, overrides)
        decl = ' '.join(f'{name}: {value};' for name, value in effective_overrides.items())
        obj_name = widget.objectName().strip()
        return f'#{obj_name} {{ {decl} }}' if obj_name else decl

    def _effective_style_overrides(self, widget: QWidget, overrides: dict[str, str]) -> dict[str, str]:
        effective_overrides = dict(overrides)
        if (
            any(name in effective_overrides for name in {'background', 'background-color'})
            and 'border-radius' not in effective_overrides
        ):
            if (radius := self._current_theme_border_radius(widget)):
                has_border_override = self._has_border_override(effective_overrides)
                if not self._has_theme_border(widget) and not has_border_override:
                    effective_overrides['border'] = 'none'
                effective_overrides['border-radius'] = radius
        return effective_overrides

    def _reset_widget_style(self, widget: QWidget, base_style: str) -> None:
        if widget.styleSheet() != base_style:
            widget.setStyleSheet(base_style)
        widget.setProperty('_themeAnimationStyleManaged', False)

    def _apply_managed_widget_style(self, widget: QWidget, base_style: str, blocks: list[str]) -> None:
        style = f'{base_style}\n' + '\n'.join(blocks) if base_style else '\n'.join(blocks)
        if widget.styleSheet() != style:
            widget.setStyleSheet(style)
        widget.setProperty('_themeAnimationStyleManaged', True)

    def _current_theme_border_radius(self, widget: QWidget) -> str:
        radius = widget.property('_themeBorderRadius')
        if not isinstance(radius, str) or not radius.strip():
            return ''

        radius_value = self._parse_measure_value(radius)
        if radius_value is None:
            return radius.strip()

        width = float(widget.width())
        height = float(widget.height())
        if width <= 0.0 or height <= 0.0:
            return radius.strip()

        max_radius = self._safe_background_radius(min(width, height))
        return f'{max(0.0, min(float(radius_value), max_radius)):g}px'

    def _safe_background_radius(self, base_size: float) -> float:
        max_radius = max(0.0, float(base_size) / 2.0)
        if max_radius <= 1.0:
            return max_radius
        return max(0.0, max_radius - 1.0)

    def _has_theme_border(self, widget: QWidget) -> bool:
        declarations = self._collect_widget_declarations(widget)
        width_text = declarations.get('border-width')
        style_text = declarations.get('border-style')
        if border_text := declarations.get('border'):
            short_width, short_style, _short_color = self._parse_border_shorthand(border_text)
            width_text = width_text or short_width
            style_text = style_text or short_style

        width = self._parse_measure_value(width_text)
        style = str(style_text or '').strip().lower()
        return bool(width and width > 0.0 and style and style != 'none')

    def _has_border_override(self, overrides: dict[str, str]) -> bool:
        return any(name == 'border' or name.startswith('border-') for name in overrides)

    def _build_slider_override_blocks(self, widget: QWidget, overrides: dict[str, dict[str, str]]) -> list[str]:
        if not overrides:
            return []

        obj_name = widget.objectName().strip()
        if not obj_name:
            return []

        blocks: list[str] = []
        for part, rules in overrides.items():
            if not rules:
                continue
            for orientation in ('horizontal', 'vertical'):
                decls: list[str] = []
                for name, raw_value in rules.items():
                    value = str(raw_value).strip()
                    if not value:
                        continue
                    if name == 'size':
                        metric = 'height' if orientation == 'horizontal' else 'width'
                        decls.append(f'{metric}: {value};')
                    else:
                        decls.append(f'{name}: {value};')
                if decls:
                    blocks.append(f'#{obj_name}::{part}:{orientation} {{ ' + ' '.join(decls) + ' }')
        return blocks

    def _sample_color(self, widget: QWidget, css_property: str, fallback: QColor) -> QColor:
        role = QPalette.ColorRole.WindowText if css_property == 'color' else QPalette.ColorRole.Window
        color = widget.palette().color(role)
        if color.isValid():
            return color
        return QColor(fallback)

    def _sample_override_color(self, widget: QWidget, css_property: str) -> QColor | None:
        state = None
        if isinstance(widget, BoxThemeMixin):
            try:
                state = widget.box_theme_state()
            except RuntimeError:
                state = None
        state_map = theme_map(state)
        if state_map is not None:
            if css_property in {'background', 'background-color'}:
                background = theme_map(state_map.get('background')) or {}
                color = background.get('color')
                if isinstance(color, QColor) and color.isValid():
                    return color
            elif css_property == 'border-color':
                border = theme_map(state_map.get('border')) or {}
                color = border.get('color')
                if isinstance(color, QColor) and color.isValid():
                    return color

        if css_property.startswith('parts.'):
            mapped = self._map_parts_css_property(widget, css_property)
            if mapped.startswith('slider.'):
                css_property = mapped
            else:
                parts = css_property.split('.', 2)
                if len(parts) == 3:
                    _, part, css_name = parts
                    if css_name in {'color', 'background-color', 'border-color'} or css_name.startswith('states.'):
                        if isinstance(widget, MTComboBox):
                            color = widget.current_part_color(part, css_name)
                            if color.isValid():
                                return color
                        elif isinstance(widget, (MTSlider, MTSwitch)):
                            color = widget.current_part_color(part)
                            if isinstance(color, QColor) and color.isValid():
                                return color
                return None
        if css_property.startswith('slider.'):
            parts = css_property.split('.', 2)
            if len(parts) != 3:
                return None
            _, part, css_name = parts
            raw = self._slider_style_overrides.get(widget, {}).get(part, {}).get(css_name)
        else:
            raw = self._style_overrides.get(widget, {}).get(css_property)
        return to_qcolor(raw) if isinstance(raw, str) else None

    def _sample_style_color(self, styles: dict[str, Any], property_key: str) -> QColor | None:
        raw: Any = None
        if property_key.startswith('slider.'):
            tokens = property_key.split('.')
            if len(tokens) == 4:
                _, part, group, key = tokens
                if (
                    part in {'groove', 'sub_page', 'add_page', 'handle'}
                    and group in {'background', 'border'}
                    and key == 'color'
                ):
                    parts_theme = theme_map(styles.get('parts')) or {}
                    part_data = theme_map(parts_theme.get(part))
                    group_data = theme_map(None if part_data is None else part_data.get(group))
                    if group_data is not None:
                        raw = group_data.get('color')
        elif property_key.startswith('parts.'):
            tokens = property_key.split('.')
            if len(tokens) >= 3:
                parts_theme = theme_map(styles.get('parts')) or {}
                part = tokens[1]
                suffix = tokens[2:]
                part_data = theme_map(parts_theme.get(part))
                if suffix == ['color']:
                    if part_data is not None:
                        raw = part_data.get('color')
                elif suffix == ['background', 'color']:
                    if part in {'groove', 'sub_page', 'add_page', 'handle'}:
                        group_data = theme_map(None if part_data is None else part_data.get('background'))
                        if group_data is not None:
                            raw = group_data.get('color')
                    elif part_data is not None:
                        background = theme_map(part_data.get('background')) or {}
                        raw = background.get('color')
                elif suffix == ['text', 'color']:
                    if part_data is not None:
                        text = theme_map(part_data.get('text')) or {}
                        raw = text.get('color')
                elif suffix == ['border', 'color']:
                    if part in {'groove', 'sub_page', 'add_page', 'handle'}:
                        group_data = theme_map(None if part_data is None else part_data.get('border'))
                        if group_data is not None:
                            raw = group_data.get('color')
                    elif part_data is not None:
                        border = theme_map(part_data.get('border')) or {}
                        raw = border.get('color')
        else:
            match property_key:
                case 'background.color':
                    background = theme_map(styles.get('background'))
                    raw = None if background is None else background.get('color')
                case 'color':
                    text = theme_map(styles.get('text'))
                    raw = None if text is None else text.get('color')
                case 'border.color':
                    border = theme_map(styles.get('border'))
                    raw = None if border is None else border.get('color')
                case _:
                    raw = None
        return to_qcolor(raw) if isinstance(raw, str) else None

    def _sample_style_gradient(
        self,
        styles: dict[str, Any],
        property_key: str,
        *,
        fallback: dict[str, Any],
    ) -> dict[str, Any] | None:
        source: dict[str, Any] | None = None
        if property_key == 'background.gradient':
            source = theme_map(styles.get('background'))
        elif property_key.startswith('parts.'):
            tokens = property_key.split('.')
            if len(tokens) == 4 and tokens[2] == 'background' and tokens[3] == 'gradient':
                parts_theme = theme_map(styles.get('parts')) or {}
                part_data = theme_map(parts_theme.get(tokens[1])) or {}
                source = theme_map(part_data.get('background'))
        if source is None:
            return None

        gradient_data = source.get('gradient')
        gradient_map = object_map(gradient_data)
        if gradient_map is not None:
            return normalize_gradient(gradient_map)

        color_data = source.get('color')
        color_map = object_map(color_data)
        if color_map is not None:
            return normalize_gradient(color_map)

        if isinstance(color_data, str) and (color := to_qcolor(color_data)) is not None:
            gradient = clone_gradient(fallback)
            gradient['stops'] = [(float(pos), QColor(color)) for pos, _ in gradient.get('stops', [])]
            return gradient
        return None

    def _sample_number(self, widget: QWidget, property_key: str, *, fallback: float) -> float:
        match property_key:
            case 'border.width':
                return self._sample_border_width(widget, fallback=fallback)
            case 'border.radius':
                return self._sample_border_radius(widget, fallback=fallback)
            case 'padding.left' | 'padding.top' | 'padding.right' | 'padding.bottom':
                side = property_key.rsplit('.', 1)[-1]
                index = {'left': 0, 'top': 1, 'right': 2, 'bottom': 3}.get(side, 0)
                return float(self._padding_box(widget)[index])
            case 'layout.spacing':
                layout = widget.layout()
                return float(layout.spacing()) if isinstance(layout, QLayout) else float(fallback)
            case 'layout.margin.left' | 'layout.margin.top' | 'layout.margin.right' | 'layout.margin.bottom':
                layout = widget.layout()
                if isinstance(layout, QLayout):
                    margins = layout.contentsMargins()
                    side = property_key.rsplit('.', 1)[-1]
                    index = {'left': 0, 'top': 1, 'right': 2, 'bottom': 3}.get(side, 0)
                    return float((margins.left(), margins.top(), margins.right(), margins.bottom())[index])
                return float(fallback)
            case 'widget.width':
                return float(widget.width())
            case 'widget.minimum_width':
                return float(widget.minimumWidth())
            case 'widget.maximum_width':
                maximum_width = widget.maximumWidth()
                if maximum_width >= 16777215:
                    return float(widget.width())
                return float(maximum_width)
            case 'widget.height':
                return float(widget.height())
            case 'widget.minimum_height':
                return float(widget.minimumHeight())
            case 'widget.maximum_height':
                maximum_height = widget.maximumHeight()
                if maximum_height >= 16777215:
                    return float(widget.height())
                return float(maximum_height)
            case 'widget.x':
                return float(widget.x())
            case 'widget.y':
                return float(widget.y())
            case 'scroll.vertical':
                if isinstance(widget, QAbstractScrollArea):
                    scrollbar = widget.verticalScrollBar()
                    slider = _slider_or_none(scrollbar)
                    if slider is not None:
                        return float(slider.value())
                return float(fallback)
            case 'scroll.horizontal':
                if isinstance(widget, QAbstractScrollArea):
                    scrollbar = widget.horizontalScrollBar()
                    slider = _slider_or_none(scrollbar)
                    if slider is not None:
                        return float(slider.value())
                return float(fallback)
            case 'parts.groove.size':
                return self._sample_slider_metric(widget, 'groove', fallback=fallback)
            case 'parts.handle.width':
                return self._sample_slider_metric(widget, 'handle_width', fallback=fallback)
            case 'parts.handle.height':
                return self._sample_slider_metric(widget, 'handle_height', fallback=fallback)
            case _:
                pass
        if property_key.startswith('parts.'):
            tokens = property_key.split('.')
            if len(tokens) >= 3 and isinstance(widget, (MTComboBox, MTCollapsibleContainer)):
                try:
                    metric = widget.current_part_metric(tokens[1], tuple(tokens[2:]), fallback)
                except (RuntimeError, TypeError, ValueError):
                    return float(fallback)
                return coerce_float(metric, float(fallback)) or float(fallback)
        return float(fallback)

    def _sample_border_width(self, widget: QWidget, *, fallback: float) -> float:
        state = {}
        if isinstance(widget, BoxThemeMixin):
            try:
                state = theme_map(widget.box_theme_state()) or {}
            except RuntimeError:
                state = {}
        border = theme_map(state.get('border'))
        if border is not None:
            width = border.get('width')
            if isinstance(width, (int, float)):
                return float(width)

        declarations = self._collect_widget_declarations(widget)
        width_text = declarations.get('border-width')
        if not width_text and (border_text := declarations.get('border')):
            width_text, _style, _color = self._parse_border_shorthand(border_text)
        return self._parse_measure_value(width_text) or float(fallback)

    def _sample_border_radius(self, widget: QWidget, *, fallback: float) -> float:
        state = {}
        if isinstance(widget, BoxThemeMixin):
            try:
                state = theme_map(widget.box_theme_state()) or {}
            except RuntimeError:
                state = {}
        radius = state.get('radius')
        value = self._parse_measure_value(radius)
        if value is not None:
            return float(value)

        value = self._parse_measure_value(widget.property('_themeBorderRadius'))
        if value is not None:
            return float(value)

        declarations = self._collect_widget_declarations(widget)
        return self._parse_measure_value(declarations.get('border-radius')) or float(fallback)

    def _sample_slider_metric(self, widget: QWidget, metric: str, *, fallback: float) -> float:
        if not isinstance(widget, MTSlider):
            return float(fallback)

        if metric == 'groove':
            return widget.current_part_metric('groove', 'size', fallback)
        if metric == 'handle_width':
            return widget.current_part_metric('handle', 'width', fallback)
        if metric == 'handle_height':
            return widget.current_part_metric('handle', 'height', fallback)
        return float(fallback)

    def _resolve_wheel_scroll_delta(self, widget: QWidget, spec: AnimationSpec) -> float:
        deltas = self._wheel_event_deltas.get(widget, {})
        axis = 'vertical' if spec.property_key == 'scroll.vertical' else 'horizontal'
        delta = float(deltas.get(axis, 0.0))
        if abs(delta) < 0.001:
            return 0.0

        distance = abs(float(spec.end))
        scrollbar = None
        if isinstance(widget, QAbstractScrollArea):
            scrollbar = _slider_or_none(
                widget.verticalScrollBar() if axis == 'vertical' else widget.horizontalScrollBar()
            )

        if abs(delta) >= 1.0:
            steps = delta / 120.0
            if abs(steps) >= 0.001:
                resolved_delta = -(steps * distance)
                if scrollbar is not None:
                    current = float(scrollbar.value())
                    target = max(float(scrollbar.minimum()), min(float(scrollbar.maximum()), current + resolved_delta))
                    return target - current
                return resolved_delta

        resolved_delta = -math.copysign(distance, delta)
        if scrollbar is not None:
            current = float(scrollbar.value())
            target = max(float(scrollbar.minimum()), min(float(scrollbar.maximum()), current + resolved_delta))
            return target - current
        return resolved_delta

    def _set_number_property(self, widget: QWidget, property_key: str, value: float) -> None:
        rounded = int(round(value))

        match property_key:
            case 'border.width':
                if not self._set_box_style_value(widget, 'border-width', f'{max(0.0, value):g}px'):
                    self._set_style_value(widget, 'border-width', f'{max(0.0, value):g}px')
            case 'border.radius':
                if not self._set_box_style_value(widget, 'border-radius', f'{max(0.0, value):g}px'):
                    widget.setProperty('_themeBorderRadius', f'{max(0.0, value):g}px')
                    self._set_style_value(widget, 'border-radius', f'{max(0.0, value):g}px')
            case 'padding.left' | 'padding.top' | 'padding.right' | 'padding.bottom':
                self._set_padding_side(widget, property_key.rsplit('.', 1)[-1], max(0, rounded))
            case 'layout.spacing':
                layout = widget.layout()
                if isinstance(layout, QLayout):
                    layout.setSpacing(max(0, rounded))
                    widget.updateGeometry()
            case 'layout.margin.left' | 'layout.margin.top' | 'layout.margin.right' | 'layout.margin.bottom':
                self._set_layout_margin_side(widget, property_key.rsplit('.', 1)[-1], max(0, rounded))
            case 'widget.width':
                widget.resize(max(0, rounded), widget.height())
            case 'widget.minimum_width':
                target = max(0, rounded)
                max_width = widget.maximumWidth()
                if max_width < target:
                    widget.setMaximumWidth(target)
                widget.setMinimumWidth(target)
            case 'widget.maximum_width':
                target = max(0, rounded)
                min_width = widget.minimumWidth()
                if min_width > target:
                    widget.setMinimumWidth(target)
                widget.setMaximumWidth(target)
            case 'widget.height':
                widget.resize(widget.width(), max(0, rounded))
            case 'widget.minimum_height':
                target = max(0, rounded)
                max_height = widget.maximumHeight()
                if max_height < target:
                    widget.setMaximumHeight(target)
                widget.setMinimumHeight(target)
            case 'widget.maximum_height':
                target = max(0, rounded)
                min_height = widget.minimumHeight()
                if min_height > target:
                    widget.setMinimumHeight(target)
                widget.setMaximumHeight(target)
            case 'widget.x':
                widget.move(rounded, widget.y())
            case 'widget.y':
                widget.move(widget.x(), rounded)
            case 'scroll.vertical':
                if isinstance(widget, QAbstractScrollArea):
                    scrollbar = widget.verticalScrollBar()
                    slider = _slider_or_none(scrollbar)
                    if slider is not None:
                        slider.setValue(max(slider.minimum(), min(slider.maximum(), rounded)))
            case 'scroll.horizontal':
                if isinstance(widget, QAbstractScrollArea):
                    scrollbar = widget.horizontalScrollBar()
                    slider = _slider_or_none(scrollbar)
                    if slider is not None:
                        slider.setValue(max(slider.minimum(), min(slider.maximum(), rounded)))
            case 'parts.groove.size':
                if isinstance(widget, MTSlider) and widget.set_part_metric('groove', 'size', float(max(0, rounded))):
                    return
                self._set_style_value(widget, 'parts.groove.size', f'{max(0, rounded)}px')
            case 'parts.handle.width':
                if isinstance(widget, MTSlider) and widget.set_part_metric('handle', 'width', float(max(0, rounded))):
                    return
                self._set_style_value(widget, 'parts.handle.width', f'{max(0, rounded)}px')
            case 'parts.handle.height':
                if isinstance(widget, MTSlider) and widget.set_part_metric('handle', 'height', float(max(0, rounded))):
                    return
                self._set_style_value(widget, 'parts.handle.height', f'{max(0, rounded)}px')
            case _ if property_key.startswith('parts.'):
                tokens = property_key.split('.')
                if isinstance(widget, (MTComboBox, MTCollapsibleContainer)) and len(tokens) >= 3 and widget.set_part_metric(tokens[1], tuple(tokens[2:]), float(max(0, value))):
                    return
            case _:
                return

    def _padding_box(self, widget: QWidget) -> tuple[int, int, int, int]:
        raw = widget.property('_themePaddingBox')
        sequence = cast(list[object] | tuple[object, ...] | None, raw if isinstance(raw, (list, tuple)) else None)
        if sequence is not None and len(sequence) == 4:
            values: list[int] = []
            for value in sequence:
                numeric = coerce_float(value)
                if numeric is None:
                    values.append(0)
                    continue
                values.append(max(0, int(round(numeric))))
            return (values[0], values[1], values[2], values[3])
        return (0, 0, 0, 0)

    def _set_padding_side(self, widget: QWidget, side: str, value: int) -> None:
        values = list(self._padding_box(widget))
        index = {'left': 0, 'top': 1, 'right': 2, 'bottom': 3}.get(side, 0)
        values[index] = max(0, int(value))
        widget.setProperty('_themePaddingBox', tuple(values))
        widget.updateGeometry()
        widget.update()

    def _set_layout_margin_side(self, widget: QWidget, side: str, value: int) -> None:
        layout = widget.layout()
        if not isinstance(layout, QLayout):
            self._set_padding_side(widget, side, value)
            return

        margins = layout.contentsMargins()
        values = [margins.left(), margins.top(), margins.right(), margins.bottom()]
        index = {'left': 0, 'top': 1, 'right': 2, 'bottom': 3}.get(side, 0)
        values[index] = max(0, int(value))
        layout.setContentsMargins(*values)
        widget.updateGeometry()
