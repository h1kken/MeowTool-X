from __future__ import annotations

from copy import deepcopy
from time import monotonic
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import QApplication, QWidget

from src.theme.animation.overlays import DashBorderOverlay
from src.theme.qss.targets import resolve_target_widgets
from src.theme.rainbow.border import (
    build_native_border_transition_rules,
    combine_with_scoped_rules,
    detect_border_config,
    mix_border_color,
)
from src.theme.rainbow.palette import sample_rainbow_color
from src.ui.widgets.main.box import BoxThemeMixin
from src.ui.widgets import MTSlider, MTSwitch

_FADE_DURATION_MS = 200.0
_FALLBACK_BORDER_WIDTH = 1.0
_FALLBACK_BORDER_RADIUS = 0.0
_DEFAULT_BORDER_TARGET_SELECTORS: tuple[str, ...] = (
    'MTButtonSetting',
    'MTCheckBoxSetting',
    'MTSwitchSetting',
    'MTSwitchRowSetting',
    'MTComboBoxSetting',
    'MTPathSetting',
    'MTTextSetting',
    'MTSliderSetting',
    '*_Info_Row',
    'MTButton',
)
_RUNTIME_BORDER_TARGET_PROPERTY = '_rainbowRuntimeBorderTarget'


class RainbowRuntimeController(QObject):
    def __init__(self, root: QWidget) -> None:
        super().__init__(root)
        self._root = root
        self._animation_manager: Any = None
        self._border_target_selectors: tuple[str, ...] = _DEFAULT_BORDER_TARGET_SELECTORS
        self._enabled = False
        self._duration_ms = 5000
        self._palette = 'Pastel'
        self._saturation = 0.6
        self._epoch = monotonic()
        self._last_tick_time = monotonic()
        self._filtered_widgets: set[QWidget] = set()
        self._switches: set[MTSwitch] = set()
        self._sliders: set[MTSlider] = set()
        self._setting_overlays: dict[QWidget, DashBorderOverlay] = {}
        self._setting_base_styles: dict[QWidget, str] = {}
        self._setting_states: dict[QWidget, dict[str, float]] = {}
        self._setting_configs: dict[QWidget, dict[str, float]] = {}
        self._syncing_native_border_styles: set[QWidget] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def bind_animation_manager(self, manager: Any) -> None:
        self._animation_manager = manager

    def set_enabled(self, enabled: bool, duration_ms: int | float, saturation: float = 0.6, palette: str = 'Pastel') -> None:
        if not enabled:
            self.clear()
            return

        was_enabled = self._enabled
        previous_phase = self._phase() if was_enabled else 0.0
        self._enabled = True
        self._duration_ms = max(1, int(round(float(duration_ms))))
        self._palette = str(palette or 'Pastel').strip() or 'Pastel'
        self._saturation = max(0.0, min(float(saturation), 1.0))
        self._epoch = monotonic() - ((previous_phase * float(self._duration_ms)) / 1000.0)
        self._last_tick_time = monotonic()
        self._rebuild_targets()

    def refresh(self) -> None:
        if not self._enabled:
            return
        self._rebuild_targets()

    def set_border_target_selectors(self, selectors: list[str] | tuple[str, ...]) -> None:
        normalized = tuple(
            selector.strip()
            for selector in selectors
            if selector.strip()
        )
        self._border_target_selectors = normalized or _DEFAULT_BORDER_TARGET_SELECTORS
        if self._enabled:
            self._rebuild_targets()

    def clear(self) -> None:
        self._enabled = False
        self._timer.stop()
        self._last_tick_time = monotonic()

        for widget in list(self._switches | self._sliders):
            self._clear_widget_rainbow(widget)
        for overlay in list(self._setting_overlays.values()):
            try:
                overlay.hide()
                overlay.deleteLater()
            except RuntimeError:
                continue

        for widget in list(self._setting_base_styles.keys()):
            self._restore_runtime_border(widget)

        for widget in list(self._filtered_widgets):
            try:
                widget.removeEventFilter(self)
            except RuntimeError:
                continue

        self._filtered_widgets.clear()
        self._switches.clear()
        self._sliders.clear()
        self._setting_overlays.clear()
        self._setting_base_styles.clear()
        self._setting_states.clear()
        self._setting_configs.clear()
        self._syncing_native_border_styles.clear()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(obj, QWidget):
            return super().eventFilter(obj, event)

        overlay = self._setting_overlays.get(obj)
        if obj not in self._setting_states and overlay is None:
            return super().eventFilter(obj, event)

        match event.type():
            case QEvent.Type.Enter:
                self._set_border_target_opacity(obj, 1.0)
                if overlay is not None and obj.isVisible():
                    overlay.show()
            case QEvent.Type.Leave:
                self._set_border_target_opacity(obj, 0.0)
            case QEvent.Type.Resize | QEvent.Type.Move | QEvent.Type.Show:
                if overlay is not None:
                    self._sync_overlay_geometry(obj)
                if overlay is not None and event.type() == QEvent.Type.Show and obj.isVisible() and self._setting_states.get(obj, {}).get('opacity', 0.0) > 0.0:
                    overlay.show()
            case QEvent.Type.StyleChange:
                self._handle_external_style_change(obj)
            case QEvent.Type.Hide:
                if overlay is not None:
                    try:
                        overlay.hide()
                    except RuntimeError:
                        pass
            case _:
                pass

        return super().eventFilter(obj, event)

    def _set_border_target_opacity(self, widget: QWidget, target_opacity: float) -> None:
        state = self._setting_states.get(widget)
        if not isinstance(state, dict):
            return
        state['target_opacity'] = max(0.0, min(float(target_opacity), 1.0))

    def _rebuild_targets(self) -> None:
        previous_switches = set(self._switches)
        previous_sliders = set(self._sliders)
        previous_filtered = set(self._filtered_widgets)
        previous_states = {
            widget: dict(state)
            for widget, state in self._setting_states.items()
        }
        current_filtered: set[QWidget] = set()

        for widget in list(previous_switches | previous_sliders):
            self._clear_widget_rainbow(widget)
        for overlay in list(self._setting_overlays.values()):
            try:
                overlay.hide()
                overlay.deleteLater()
            except RuntimeError:
                continue

        for widget in list(self._setting_base_styles.keys()):
            self._restore_runtime_border(widget)

        self._switches.clear()
        self._sliders.clear()
        self._setting_overlays.clear()
        self._setting_base_styles.clear()
        self._setting_states.clear()
        self._setting_configs.clear()
        self._syncing_native_border_styles.clear()

        for widget in resolve_target_widgets(self._root, 'MTSwitch', include_window=True):
            if not isinstance(widget, MTSwitch):
                continue
            self._install_filter(widget, current_filtered)
            self._switches.add(widget)

        for widget in resolve_target_widgets(self._root, 'MTSlider', include_window=True):
            if not isinstance(widget, MTSlider):
                continue
            self._install_filter(widget, current_filtered)
            self._sliders.add(widget)

        for widget in self._iter_border_target_widgets():
            config = detect_border_config(
                widget,
                fallback_width=_FALLBACK_BORDER_WIDTH,
                fallback_radius=_FALLBACK_BORDER_RADIUS,
            )
            if not config.get('native'):
                box_border_visible = self._box_theme_has_visible_border(widget)
                if box_border_visible and self._prepare_box_painted_config(widget, config):
                    pass
            self._install_filter(widget, current_filtered)
            try:
                widget.setProperty(_RUNTIME_BORDER_TARGET_PROPERTY, True)
            except RuntimeError:
                continue
            is_active = self._border_target_is_active(widget)
            previous_state = previous_states.get(widget, {})
            current_opacity = max(0.0, min(float(previous_state.get('opacity', 0.0)), 1.0))
            self._setting_base_styles[widget] = widget.styleSheet()
            self._setting_states[widget] = {
                'opacity': current_opacity,
                'target_opacity': 1.0 if is_active else 0.0,
            }
            config['native_applied'] = False
            self._setting_configs[widget] = config
            if not config.get('native'):
                overlay = DashBorderOverlay(widget)
                overlay.configure(
                    color=sample_rainbow_color(
                        0.0,
                        palette=self._palette,
                        saturation=self._saturation,
                    ),
                    width=float(config['width']),
                    radius=float(config['radius']),
                    dash_pattern=list(config.get('dash_pattern', [9999.0, 1.0])),
                    inset=float(config['inset']),
                    pen_style=config.get('pen_style', Qt.PenStyle.SolidLine),
                    opacity=current_opacity,
                )
                self._setting_overlays[widget] = overlay
                self._sync_overlay_geometry(widget)
                if widget.isVisible() and current_opacity > 0.0:
                    overlay.show()

        for widget in previous_filtered - current_filtered:
            try:
                widget.removeEventFilter(self)
            except RuntimeError:
                continue
        self._filtered_widgets = current_filtered

        if self._switches or self._sliders or self._setting_states:
            self._tick()
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def _install_filter(self, widget: QWidget, current_filtered: set[QWidget]) -> None:
        current_filtered.add(widget)
        if widget in self._filtered_widgets:
            return
        widget.installEventFilter(self)

    def _sync_overlay_geometry(self, widget: QWidget) -> None:
        overlay = self._setting_overlays.get(widget)
        if overlay is None:
            return
        was_visible = overlay.isVisible()
        overlay.setGeometry(widget.rect())
        overlay.raise_()
        if was_visible and widget.isVisible():
            overlay.show()

    def _tick(self) -> None:
        if not self._enabled:
            self._timer.stop()
            return

        now = monotonic()
        fade_step = min(1.0, max(0.0, (now - self._last_tick_time) * 1000.0) / _FADE_DURATION_MS)
        self._last_tick_time = now
        phase = self._phase()
        for widget in list(self._switches):
            if not self._widget_is_alive(widget):
                self._switches.discard(widget)
                continue
            if not widget.isVisible():
                continue
            if widget.isChecked():
                self._set_widget_rainbow(widget, phase)
            else:
                self._clear_widget_rainbow(widget)

        for widget in list(self._sliders):
            if not self._widget_is_alive(widget):
                self._sliders.discard(widget)
                continue
            if not widget.isVisible():
                continue
            self._set_widget_rainbow(widget, phase)

        color = sample_rainbow_color(
            phase,
            palette=self._palette,
            saturation=self._saturation,
        )
        for widget in list(self._setting_states.keys()):
            overlay = self._setting_overlays.get(widget)
            config = self._setting_configs.get(widget, {})
            if not self._widget_is_alive(widget):
                self._restore_runtime_border(widget)
                self._setting_overlays.pop(widget, None)
                self._setting_base_styles.pop(widget, '')
                self._setting_states.pop(widget, None)
                self._setting_configs.pop(widget, None)
                self._syncing_native_border_styles.discard(widget)
                if overlay is not None:
                    try:
                        overlay.hide()
                        overlay.deleteLater()
                    except RuntimeError:
                        pass
                continue
            if not widget.isVisible():
                if config.get('native_applied'):
                    self._restore_native_border(widget)
                    config['native_applied'] = False
                if overlay is not None and overlay.isVisible():
                    overlay.hide()
                continue

            state = self._setting_states.setdefault(widget, {'opacity': 0.0, 'target_opacity': 0.0})
            state['target_opacity'] = 1.0 if self._border_target_is_active(widget) else 0.0
            opacity = float(state.get('opacity', 0.0))
            target = float(state.get('target_opacity', 0.0))
            if target > opacity:
                opacity = min(target, opacity + fade_step)
            elif target < opacity:
                opacity = max(target, opacity - fade_step)
            state['opacity'] = opacity

            if opacity <= 0.0 and target <= 0.0 and not config.get('native_applied'):
                if overlay is not None and overlay.isVisible():
                    overlay.hide()
                continue

            if config.get('native'):
                self._sync_native_border_color(widget, config, color, opacity)
                if overlay is not None:
                    overlay.hide()
                continue

            if overlay is None:
                continue

            overlay.set_color(color)
            overlay.set_opacity(opacity)
            if widget.isVisible() and opacity > 0.0:
                overlay.show()
            else:
                overlay.hide()

    def _phase(self) -> float:
        elapsed_ms = (monotonic() - self._epoch) * 1000.0
        if self._duration_ms <= 0:
            return 0.0
        return (elapsed_ms % float(self._duration_ms)) / float(self._duration_ms)

    def _set_widget_rainbow(self, widget: QWidget, phase: float) -> None:
        if isinstance(widget, MTSlider):
            try:
                widget.set_slider_line_rainbow_palette(self._palette)
                widget.set_slider_line_rainbow_saturation(self._saturation)
                widget.set_slider_line_rainbow(float(phase))
            except RuntimeError:
                return
            return
        if isinstance(widget, MTSwitch):
            try:
                widget.set_handle_rainbow_palette(self._palette)
                widget.set_handle_rainbow_saturation(self._saturation)
                widget.set_handle_rainbow(float(phase))
            except RuntimeError:
                return

    def _clear_widget_rainbow(self, widget: QWidget) -> None:
        if isinstance(widget, MTSlider):
            try:
                widget.clear_slider_line_rainbow()
            except RuntimeError:
                return
            return
        if isinstance(widget, MTSwitch):
            try:
                widget.clear_handle_rainbow()
            except RuntimeError:
                return

    def _widget_is_alive(self, widget: QWidget) -> bool:
        try:
            widget.objectName()
        except RuntimeError:
            return False
        return True

    def _iter_border_target_widgets(self) -> list[QWidget]:
        widgets: list[QWidget] = []
        seen: set[QWidget] = set()
        explicit_widgets: list[QWidget] = []
        explicit_seen: set[QWidget] = set()

        for selector in self._border_target_selectors:
            for widget in resolve_target_widgets(self._root, selector, include_window=True):
                if widget in seen:
                    continue
                if widget.property('rainbowBorderExcluded') is True:
                    continue
                if widget.property('rainbowBorderTarget') is False:
                    continue
                seen.add(widget)
                widgets.append(widget)

        for widget in self._root.findChildren(QWidget):
            if widget.property('rainbowBorderExcluded') is True:
                continue
            if bool(widget.property('rainbowBorderTarget')):
                if widget not in explicit_seen:
                    explicit_seen.add(widget)
                    explicit_widgets.append(widget)

        explicit_set = set(explicit_widgets)
        filtered: list[QWidget] = []
        for widget in widgets:
            if widget not in explicit_set and self._has_border_target_parent(widget, widgets):
                continue
            filtered.append(widget)

        for widget in explicit_widgets:
            if widget not in filtered:
                filtered.append(widget)

        return filtered

    def _has_border_target_parent(
        self,
        widget: QWidget,
        candidates: list[QWidget],
    ) -> bool:
        candidate_set = set(candidates)
        parent = widget.parentWidget()
        while parent is not None:
            if parent in candidate_set:
                return True
            parent = parent.parentWidget()
        return False

    def _border_target_is_active(self, widget: QWidget) -> bool:
        try:
            if self._cursor_is_inside_widget(widget):
                return True
            if widget.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents):
                parent = widget.parentWidget()
                return bool(parent is not None and self._cursor_is_inside_widget(parent))
        except RuntimeError:
            return False
        return False

    def _cursor_is_inside_widget(self, widget: QWidget) -> bool:
        if not widget.isVisible() or not widget.isEnabled():
            return False

        global_pos = QCursor.pos()
        local_pos = widget.mapFromGlobal(global_pos)
        if not (widget.rect().contains(local_pos) and widget.visibleRegion().contains(local_pos)):
            return False

        top_widget = QApplication.widgetAt(global_pos)
        if top_widget is None:
            return False

        current: QWidget | None = top_widget
        while current is not None:
            if current is widget:
                return True
            current = current.parentWidget()
        return False

    def _handle_external_style_change(self, widget: QWidget) -> None:
        if widget in self._syncing_native_border_styles:
            return

        config = self._setting_configs.get(widget)
        state = self._setting_states.get(widget)
        if not isinstance(config, dict) or not config.get('native') or not isinstance(state, dict):
            return
        if config.get('box_painted'):
            return

        try:
            self._setting_base_styles[widget] = widget.styleSheet()
        except RuntimeError:
            return

        config['native_applied'] = False
        opacity = float(state.get('opacity', 0.0))
        if opacity <= 0.0:
            return

        self._sync_native_border_color(
            widget,
            config,
            sample_rainbow_color(
                self._phase(),
                palette=self._palette,
                saturation=self._saturation,
            ),
            opacity,
        )

    def _sync_native_border_color(self, widget: QWidget, config: dict[str, Any], color: QColor, opacity: float) -> None:
        if opacity <= 0.0:
            self._restore_native_border(widget)
            config['native_applied'] = False
            return

        if self._sync_custom_box_border_color(widget, config, color, opacity):
            return

        base_style = self._setting_base_styles.get(widget, '')
        rules = build_native_border_transition_rules(config, color, opacity)
        target_style = combine_with_scoped_rules(widget, base_style, rules)
        try:
            if widget.styleSheet() != target_style:
                self._syncing_native_border_styles.add(widget)
                widget.setStyleSheet(target_style)
        except RuntimeError:
            return
        finally:
            self._syncing_native_border_styles.discard(widget)
        config['native_applied'] = True

    def _sync_custom_box_border_color(self, widget: QWidget, config: dict[str, Any], color: QColor, opacity: float) -> bool:
        if not isinstance(widget, BoxThemeMixin):
            return False

        mixed = mix_border_color(self._base_border_color(config), color, opacity)
        try:
            if not widget.set_box_border(
                color=mixed,
                width=config.get('width'),
                radius=config.get('radius'),
                style=str(config.get('style', 'solid') or 'solid'),
            ):
                return False
        except RuntimeError:
            return False

        config['native_applied'] = True
        return True

    def _restore_native_border(self, widget: QWidget) -> None:
        config = self._setting_configs.get(widget)
        if not isinstance(config, dict) or not config.get('native_applied'):
            return
        if config.get('box_painted'):
            self._restore_box_border(widget, config)
            config['native_applied'] = False
            return
        if isinstance(widget, BoxThemeMixin):
            base_color = self._base_border_color(config)
            if base_color:
                widget.set_box_border(color=base_color)
                config['native_applied'] = False
                return
        base_style = self._setting_base_styles.get(widget, '')
        try:
            if widget.styleSheet() != base_style:
                self._syncing_native_border_styles.add(widget)
                widget.setStyleSheet(base_style)
        except RuntimeError:
            return
        finally:
            self._syncing_native_border_styles.discard(widget)
        config['native_applied'] = False

    def _restore_runtime_border(self, widget: QWidget) -> None:
        config = self._setting_configs.get(widget)
        if isinstance(config, dict):
            if config.get('box_painted'):
                self._restore_box_border(widget, config)

        base_style = self._setting_base_styles.get(widget, '')
        try:
            widget.setProperty(_RUNTIME_BORDER_TARGET_PROPERTY, False)
            if widget.styleSheet() != base_style:
                widget.setStyleSheet(base_style)
        except RuntimeError:
            pass

    def _prepare_box_painted_config(self, widget: QWidget, config: dict[str, Any]) -> bool:
        if not isinstance(widget, BoxThemeMixin):
            return False

        config['native'] = True
        config['box_painted'] = True
        config['box_theme_state'] = widget.box_theme_state()
        config['border_color_text'] = '#00000000'
        return True

    def _box_theme_has_visible_border(self, widget: QWidget) -> bool:
        if not isinstance(widget, BoxThemeMixin):
            return False

        raw_state = widget.box_theme_state()
        if not isinstance(raw_state, dict):
            return False
        state: dict[str, Any] = raw_state

        border = state.get('border')
        if not isinstance(border, dict):
            return False
        border_data: dict[str, Any] = cast(dict[str, Any], border)

        if self._border_part_is_visible(border_data):
            return True

        for side in ('top', 'right', 'bottom', 'left'):
            side_data = border_data.get(side)
            if isinstance(side_data, dict) and self._border_part_is_visible(
                cast(dict[str, Any], side_data),
                fallback_style=border_data.get('style'),
            ):
                return True
        return False

    def _border_part_is_visible(self, data: dict[str, Any], *, fallback_style: Any = None) -> bool:
        width = data.get('width')
        if not isinstance(width, (int, float)) or float(width) <= 0.0:
            return False

        style = str(data.get('style') or fallback_style or 'solid').strip().lower()
        if style in {'', 'none', 'no', 'transparent'}:
            return False

        color = data.get('color')
        return isinstance(color, QColor) and color.isValid() and color.alpha() > 0

    def _restore_box_border(self, widget: QWidget, config: dict[str, Any]) -> None:
        if not isinstance(widget, BoxThemeMixin):
            return

        raw_saved_state = config.get('box_theme_state')
        if not isinstance(raw_saved_state, dict):
            return
        saved_state: dict[str, Any] = cast(dict[str, Any], raw_saved_state)

        raw_current_state = widget.box_theme_state()
        current_state: dict[str, Any] | None = (
            raw_current_state
            if isinstance(raw_current_state, dict) else
            None
        )
        state = deepcopy(current_state) if current_state is not None else deepcopy(saved_state)
        border = saved_state.get('border')
        if isinstance(border, dict):
            state['border'] = deepcopy(cast(dict[str, Any], border))
        if 'radius' in saved_state:
            state['radius'] = deepcopy(saved_state.get('radius'))

        try:
            widget.restore_box_theme_state(state)
        except RuntimeError:
            pass

    def _base_border_color(self, config: dict[str, Any]) -> Any:
        color = config.get('border_color')
        if isinstance(color, QColor):
            return color
        return config.get('border_color_text', '')
