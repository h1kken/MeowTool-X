from pathlib import Path
from copy import deepcopy
from typing import Any, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget
from src.utils.pyside6 import emit
from src.utils.filesystem import load_json
from src.utils.consts import GRADIENT_DIRECTIONS


class ThemeManager(QObject):
    theme_changed = Signal(dict)
    
    def __init__(self, root: QWidget, default_theme: dict):
        super().__init__()
        self._root = root
        self._default_theme = default_theme or {}
        self._current_theme = deepcopy(self._default_theme)

    def load(self, theme: Path | dict):
        if isinstance(theme, Path):
            theme = load_json(theme)
            if theme is None:
                return
        
        merged = deepcopy(self._default_theme)
        merged_widgets: dict[str, dict] = self._parse_widgets(merged.get('widgets', []))
        user_widgets: dict[str, dict] = self._parse_widgets(theme.get('widgets', []))

        for object_name, data in user_widgets.items():
            merged_widgets.setdefault(object_name, {})
            
            if (styles := data.get('styles', {})):
                merged_widgets[object_name].update(styles)
                
            if (animations := data.get('animations', {})):
                merged_widgets[object_name].setdefault('animations', {})
                merged_widgets[object_name]['animations'].update(animations)

        merged['widgets'] = merged_widgets

        if (user_meta := theme.get('meta')):
            merged['meta'].update(user_meta)

        self._current_theme = merged

    def apply(self):
        qss_parts = []
        animations = {}

        for object_name, styles in self._current_theme.get('widgets', {}).items():
            if (qss := self._build_qss(object_name, styles)):
                qss_parts.append(qss)
            if (anims := styles.get('animations')):
                animations[object_name] = anims

        self._root.setStyleSheet('\n'.join(qss_parts))
        emit(self.theme_changed, animations)

    def _parse_widgets(self, widgets: list[dict]) -> dict[str, dict]:
        parsed: dict[str, dict] = {}
        
        for item in widgets:
            targets = item.get('targets', [])
            
            for object_name in targets:
                parsed.setdefault(object_name, {})

                if (styles := item.get('styles', {})):
                    parsed[object_name].update(styles)

                if (animations := item.get('animations', {})):
                    parsed[object_name].setdefault('animations', {})
                    parsed[object_name]['animations'].update(animations)
                
        return parsed

    def _build_qss(self, object_name: str, styles: dict) -> str:
        qss: list[str] = []

        base_rules = self._build_rules(styles)
        if base_rules:
            qss.append(
                f'#{object_name} {{\n ' +
                '\n  '.join(base_rules) +
                '\n}'
            )

        reactions: dict = styles.get('reactions', {})
        for state, state_styles in reactions.items():
            rules = self._build_rules(state_styles)
            if rules:
                qss.append(
                    f'#{object_name}:{state} {{\n  ' +
                    '\n  '.join(rules) +
                    '\n}'
                )

        return '\n'.join(qss)

    def _build_rules(self, data: dict) -> list[str]:
        rules = []

        if (bg_data := data.get('background')):
                    
            if (bg_color := self._build_background_color(bg_data.get('color'))):
                rules.append(bg_color)

            if (bg_image := bg_data.get('image')): # TODO: gif, mp4, etc. supports
                rules.append(f'background-image: {bg_image};')

        if (t_data := data.get('text')):

            if (t_color := t_data.get('color')):
                rules.append(f'color: {t_color};')

            if (ft_data := t_data.get('font')):

                if (ft_family := ft_data.get('family')):
                    rules.append(f'font-family: {ft_family};')

                if (ft_size := ft_data.get('size')):
                    rules.append(f'font-size: {ft_size};')

                if (ft_weight := ft_data.get('weight')):
                    rules.append(f'font-weight: {ft_weight};')

                if (ft_style := ft_data.get('style')):
                    rules.append(f'font-style: {ft_style};')

        if (b_data := data.get('border')):
            
            if (border := self._build_border(b_data)):
                rules.append(border)
                
            if (b_radius := b_data.get('radius')):
                rules.append(f'border-radius: {b_radius};')

        return rules

    def _build_background_color(self, data: Any):
        if data is None:
            return
        
        if isinstance(data, str):
            return f'background-color: {data};'

        if isinstance(data, dict):
            return f'background: {self._build_gradient(data)};'

    def _build_gradient(self, data: dict) -> Optional[str]:
        g_type = data.get('type', 'linear')
        g_stops = data.get('stops')
        if not g_stops:
            return

        g_stop_str = ', '.join(f'stop:{pos} {color}' for pos, color in g_stops)

        match g_type:
            case 'linear':
                g_dir = data.get('direction', 'vertical')

                x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(g_dir, (0, 0, 0, 1))

                return f'qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {g_stop_str})'
                
            case 'radial':
                cx, cy = data.get('center', (0.5, 0.5))
                radius = data.get('radius', 0.5)

                return f'qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {g_stop_str})'

    def _build_border(self, data: dict) -> Optional[str]:
        w = data.get('width')
        s = data.get('style')
        c = data.get('color')
        if all((w, s, c)):
            return f'border: {w} {s} {c};'
