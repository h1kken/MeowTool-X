"""
Extended CSS Properties for Theme System

This module provides support for additional CSS-like properties
that can be used in theme definitions for enhanced visual effects.
"""

from typing import Any, Mapping, Sequence, cast


# CSS Properties that can be used in theme definitions
CSS_PROPERTIES: dict[str, str] = {
    # Standard properties
    'background_color': 'background-color',
    'text_color': 'color',
    'border_color': 'border-color',
    'border_width': 'border-width',
    'border_style': 'border-style',
    'border_radius': 'border-radius',
    'opacity': 'opacity',
    'cursor': 'cursor',
    
    # Extended properties
    'shadow': 'box-shadow',
    'transform': 'transform',
    'filter': 'filter',
    'transition': 'transition',
    'animation': 'animation',
    'outline': 'outline',
    
    # Layout properties
    'min_width': 'min-width',
    'max_width': 'max-width',
    'min_height': 'min-height',
    'max_height': 'max-height',
    'width': 'width',
    'height': 'height',
    
    # Typography
    'font_family': 'font-family',
    'font_size': 'font-size',
    'font_weight': 'font-weight',
    'font_style': 'font-style',
    'text_decoration': 'text-decoration',
    'text_align': 'text-align',
    'line_height': 'line-height',
    'text_transform': 'text-transform',
    
    # Spacing
    'margin': 'margin',
    'margin_top': 'margin-top',
    'margin_right': 'margin-right',
    'margin_bottom': 'margin-bottom',
    'margin_left': 'margin-left',
    'padding': 'padding',
    'padding_top': 'padding-top',
    'padding_right': 'padding-right',
    'padding_bottom': 'padding-bottom',
    'padding_left': 'padding-left',
    
    # Flexbox
    'flex': 'flex',
    'flex_grow': 'flex-grow',
    'flex_shrink': 'flex-shrink',
    'flex_basis': 'flex-basis',
    'flex_direction': 'flex-direction',
    'flex_wrap': 'flex-wrap',
    'justify_content': 'justify-content',
    'align_items': 'align-items',
    'align_content': 'align-content',
    'gap': 'gap',
    
    # Grid
    'display': 'display',
    'grid_template_columns': 'grid-template-columns',
    'grid_template_rows': 'grid-template-rows',
    'grid_column': 'grid-column',
    'grid_row': 'grid-row',
    'grid_area': 'grid-area',
    
    # Effects
    'blur': 'filter',
    'brightness': 'filter',
    'contrast': 'filter',
    'grayscale': 'filter',
    'hue_rotate': 'filter',
    'invert': 'filter',
    'saturate': 'filter',
    'sepia': 'filter',
    'drop_shadow': 'filter',
    
    # Transitions
    'transition_property': 'transition-property',
    'transition_duration': 'transition-duration',
    'transition_timing_function': 'transition-timing-function',
    'transition_delay': 'transition-delay',
    
    # Animations
    'animation_name': 'animation-name',
    'animation_duration': 'animation-duration',
    'animation_timing_function': 'animation-timing-function',
    'animation_delay': 'animation-delay',
    'animation_iteration_count': 'animation-iteration-count',
    'animation_direction': 'animation-direction',
    'animation_fill_mode': 'animation-fill-mode',
    'animation_play_state': 'animation-play-state',
    
    # Visual effects
    'backdrop_filter': 'backdrop-filter',
    'mix_blend_mode': 'mix-blend-mode',
    'clip_path': 'clip-path',
    'mask': 'mask',
    'shape_outside': 'shape-outside',
    
    # Other
    'overflow': 'overflow',
    'overflow_x': 'overflow-x',
    'overflow_y': 'overflow-y',
    'visibility': 'visibility',
    'z_index': 'z-index',
    'content': 'content',
    'quotes': 'quotes',
    'counter_increment': 'counter-increment',
    'counter_reset': 'counter-reset',
}


class CssPropertyConverter:
    """Converts theme property names to CSS property names."""
    
    @staticmethod
    def to_css(property_name: str) -> str:
        """Convert a theme property name to its CSS equivalent."""
        return CSS_PROPERTIES.get(property_name, property_name)
    
    @staticmethod
    def is_extended(property_name: str) -> bool:
        """Check if a property is an extended (non-standard) property."""
        return property_name in CSS_PROPERTIES
    
    @staticmethod
    def get_all_properties() -> list[str]:
        """Get all available CSS properties."""
        return list(CSS_PROPERTIES.keys())


class ShadowBuilder:
    """Builder for CSS box-shadow values."""
    
    @staticmethod
    def build(
        offset_x: str = '2px',
        offset_y: str = '2px',
        blur: str = '4px',
        spread: str = '0px',
        color: str = '#00000080',
        inset: bool = False,
    ) -> str:
        """
        Build a CSS box-shadow value.
        
        Args:
            offset_x: Horizontal offset (e.g., '2px', '4px')
            offset_y: Vertical offset (e.g., '2px', '4px')
            blur: Blur radius (e.g., '4px', '8px')
            spread: Spread radius (e.g., '0px', '2px')
            color: Shadow color (supports RGBA for transparency)
            inset: Whether to render shadow inside the element
        
        Returns:
            CSS box-shadow value string
        """
        prefix = 'inset ' if inset else ''
        return f'{prefix}{offset_x} {offset_y} {blur} {spread} {color}'
    
    @staticmethod
    def parse(shadow_string: str) -> dict[str, Any] | None:
        """
        Parse a CSS box-shadow value into components.
        
        Args:
            shadow_string: CSS box-shadow value (e.g., '2px 2px 4px 0px #00000080')
        
        Returns:
            Dictionary with shadow components or None if parsing fails
        """
        parts = shadow_string.strip().split()
        if len(parts) < 5:
            return None
        
        inset = parts[0].lower() == 'inset'
        offset = 1 if inset else 0
        
        return {
            'inset': inset,
            'offset_x': parts[offset],
            'offset_y': parts[offset + 1],
            'blur': parts[offset + 2],
            'spread': parts[offset + 3],
            'color': parts[offset + 4],
        }


class TransformBuilder:
    """Builder for CSS transform values."""
    
    @staticmethod
    def build(operations: Sequence[Mapping[str, Any]]) -> str:
        """
        Build a CSS transform value from operations.
        
        Args:
            operations: List of transform operations
                e.g., [{'rotate': 45}, {'scale': 1.5}, {'translate': (10, 20)}]
        
        Returns:
            CSS transform value string
        """
        transforms: list[str] = []
        
        for op in operations:
            if 'rotate' in op:
                angle = op['rotate']
                transforms.append(f'rotate({angle}deg)')
            elif 'rotate_x' in op:
                transforms.append(f'rotateX({op["rotate_x"]}deg)')
            elif 'rotate_y' in op:
                transforms.append(f'rotateY({op["rotate_y"]}deg)')
            elif 'rotate_z' in op:
                transforms.append(f'rotateZ({op["rotate_z"]}deg)')
            elif 'scale' in op:
                scale = op['scale']
                if isinstance(scale, (int, float)):
                    transforms.append(f'scale({scale})')
                elif isinstance(scale, (list, tuple)):
                    scale_values = cast(list[Any] | tuple[Any, ...], scale)
                    if len(scale_values) >= 2:
                        transforms.append(
                            f'scale({scale_values[0]}, {scale_values[1]})'
                        )
            elif 'translate' in op:
                trans = op['translate']
                if isinstance(trans, (int, float)):
                    transforms.append(f'translate({trans}px)')
                elif isinstance(trans, (list, tuple)):
                    trans_values = cast(list[Any] | tuple[Any, ...], trans)
                    if len(trans_values) >= 2:
                        transforms.append(
                            f'translate({trans_values[0]}px, {trans_values[1]}px)'
                        )
            elif 'skew' in op:
                skew = op['skew']
                if isinstance(skew, (int, float)):
                    transforms.append(f'skew({skew}deg)')
                elif isinstance(skew, (list, tuple)):
                    skew_values = cast(list[Any] | tuple[Any, ...], skew)
                    if len(skew_values) >= 2:
                        transforms.append(
                            f'skew({skew_values[0]}deg, {skew_values[1]}deg)'
                        )
            elif 'perspective' in op:
                transforms.append(f'perspective({op["perspective"]}px)')
        
        return ' '.join(transforms) if transforms else 'none'
    
    @staticmethod
    def parse(transform_string: str) -> list[dict[str, Any]]:
        """
        Parse a CSS transform value into operations.
        
        Returns:
            List of transform operations
        """
        operations: list[dict[str, Any]] = []
        
        funcs = ['rotate', 'rotateX', 'rotateY', 'rotateZ', 'scale', 'translate', 'skew', 'perspective']
        
        for func in funcs:
            if func.lower() in transform_string.lower():
                operations.append({func.lower(): None})
        
        return operations


class FilterBuilder:
    """Builder for CSS filter values."""
    
    @staticmethod
    def build(filters: Sequence[Mapping[str, Any]]) -> str:
        """
        Build a CSS filter value from filter operations.
        
        Args:
            filters: List of filter operations
                e.g., [{'blur': 5}, {'brightness': 1.2}, {'drop-shadow': {...}}]
        
        Returns:
            CSS filter value string
        """
        filter_parts: list[str] = []
        
        for f in filters:
            if 'blur' in f:
                filter_parts.append(f'blur({f["blur"]}px)')
            elif 'brightness' in f:
                filter_parts.append(f'brightness({f["brightness"]})')
            elif 'contrast' in f:
                filter_parts.append(f'contrast({f["contrast"]})')
            elif 'grayscale' in f:
                filter_parts.append(f'grayscale({f["grayscale"]})')
            elif 'hue_rotate' in f:
                filter_parts.append(f'hue-rotate({f["hue_rotate"]}deg)')
            elif 'invert' in f:
                filter_parts.append(f'invert({f["invert"]})')
            elif 'saturate' in f:
                filter_parts.append(f'saturate({f["saturate"]})')
            elif 'sepia' in f:
                filter_parts.append(f'sepia({f["sepia"]})')
            elif 'drop_shadow' in f:
                shadow_data = f['drop_shadow']
                if isinstance(shadow_data, dict):
                    shadow_mapping = cast(dict[str, Any], shadow_data)
                    shadow = ShadowBuilder.build(
                        offset_x=str(shadow_mapping.get('offset_x', '2px')),
                        offset_y=str(shadow_mapping.get('offset_y', '2px')),
                        blur=str(shadow_mapping.get('blur', '4px')),
                        spread=str(shadow_mapping.get('spread', '0px')),
                        color=str(shadow_mapping.get('color', '#00000080')),
                        inset=bool(shadow_mapping.get('inset', False)),
                    )
                    filter_parts.append(f'drop-shadow({shadow})')
        
        return ' '.join(filter_parts) if filter_parts else 'none'
    
    @staticmethod
    def parse(filter_string: str) -> list[dict[str, Any]]:
        """Parse a CSS filter value into filter operations."""
        filters: list[dict[str, Any]] = []
        
        if 'blur' in filter_string:
            filters.append({'blur': 0})
        if 'brightness' in filter_string:
            filters.append({'brightness': 1})
        if 'contrast' in filter_string:
            filters.append({'contrast': 1})
        if 'grayscale' in filter_string:
            filters.append({'grayscale': 0})
        if 'hue-rotate' in filter_string:
            filters.append({'hue_rotate': 0})
        if 'invert' in filter_string:
            filters.append({'invert': 0})
        if 'saturate' in filter_string:
            filters.append({'saturate': 1})
        if 'sepia' in filter_string:
            filters.append({'sepia': 0})
        
        return filters


class TransitionBuilder:
    """Builder for CSS transition values."""
    
    @staticmethod
    def build(
        property: str = 'all',
        duration: int | str = 200,
        timing_function: str = 'ease',
        delay: int | str = 0,
    ) -> str:
        """
        Build a CSS transition value.
        
        Args:
            property: CSS property to transition (or 'all')
            duration: Transition duration in ms or as string (e.g., 200 or '200ms')
            timing_function: Easing function (ease, linear, ease-in, etc.)
            delay: Transition delay in ms or as string
        
        Returns:
            CSS transition value string
        """
        if isinstance(duration, int):
            duration = f'{duration}ms'
        if isinstance(delay, int):
            delay = f'{delay}ms'
        
        return f'{property} {duration} {timing_function} {delay}'
    
    @staticmethod
    def build_multiple(transitions: Sequence[Mapping[str, Any]]) -> str:
        """
        Build multiple CSS transitions.
        
        Args:
            transitions: List of transition definitions
        
        Returns:
            CSS transition value string with multiple transitions
        """
        return ', '.join(
            TransitionBuilder.build(**dict(t)) for t in transitions
        )
    
    @staticmethod
    def parse(transition_string: str) -> list[dict[str, Any]]:
        """Parse a CSS transition value."""
        transitions: list[dict[str, Any]] = []
        
        for part in transition_string.split(','):
            parts = part.strip().split()
            if len(parts) >= 1:
                result: dict[str, Any] = {'property': parts[0]}
                if len(parts) >= 2:
                    result['duration'] = parts[1]
                if len(parts) >= 3:
                    result['timing_function'] = parts[2]
                if len(parts) >= 4:
                    result['delay'] = parts[3]
                transitions.append(result)
        
        return transitions


class AnimationBuilder:
    """Builder for CSS animation values."""
    
    EASING_PRESETS: dict[str, str] = {
        'ease': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
        'linear': 'linear',
        'ease-in': 'cubic-bezier(0.42, 0, 1, 1)',
        'ease-out': 'cubic-bezier(0, 0, 0.58, 1)',
        'ease-in-out': 'cubic-bezier(0.42, 0, 0.58, 1)',
    }
    
    @staticmethod
    def build(
        name: str = 'none',
        duration: int | str = 300,
        timing_function: str = 'ease',
        delay: int | str = 0,
        iteration_count: int | str = 1,
        direction: str = 'normal',
        fill_mode: str = 'none',
        play_state: str = 'running',
    ) -> str:
        """
        Build a CSS animation value.
        
        Args:
            name: Animation name (keyframes name)
            duration: Animation duration in ms
            timing_function: Easing function
            delay: Animation delay in ms
            iteration_count: Number of iterations (or 'infinite')
            direction: Animation direction (normal, reverse, alternate, etc.)
            fill_mode: Fill mode (none, forwards, backwards, both)
            play_state: Play state (running, paused)
        
        Returns:
            CSS animation value string
        """
        if isinstance(duration, int):
            duration = f'{duration}ms'
        if isinstance(delay, int):
            delay = f'{delay}ms'
        
        easing = AnimationBuilder.EASING_PRESETS.get(timing_function, timing_function)
        
        return f'{name} {duration} {easing} {delay} {iteration_count} {direction} {fill_mode} {play_state}'
    
    @staticmethod
    def parse(animation_string: str) -> dict[str, Any]:
        """Parse a CSS animation value."""
        parts = animation_string.strip().split()
        
        result: dict[str, Any] = {'name': 'none'}
        
        for part in parts:
            if part.endswith('ms') or part.endswith('s'):
                if 'duration' not in result:
                    result['duration'] = part
                else:
                    result['delay'] = part
            elif part in ('infinite', 'running', 'paused'):
                result['play_state'] = part
            elif part in ('normal', 'reverse', 'alternate', 'alternate-reverse'):
                result['direction'] = part
            elif part in ('none', 'forwards', 'backwards', 'both'):
                result['fill_mode'] = part
            elif 'cubic-bezier' in part or part in AnimationBuilder.EASING_PRESETS:
                result['timing_function'] = part
            elif part.isdigit() or part.replace('.', '', 1).isdigit():
                result['iteration_count'] = int(part) if '.' not in part else float(part)
            else:
                result['name'] = part
        
        return result


__all__ = [
    'CSS_PROPERTIES',
    'CssPropertyConverter',
    'ShadowBuilder',
    'TransformBuilder',
    'FilterBuilder',
    'TransitionBuilder',
    'AnimationBuilder',
]
