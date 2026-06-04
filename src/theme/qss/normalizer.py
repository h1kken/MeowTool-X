from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from src.theme.colors import to_qcolor


class StyleNormalizer:
    def normalize_alignment(self, data: Any) -> Qt.AlignmentFlag | None:
        if data is None:
            return None

        if isinstance(data, (list, tuple, set)):
            tokens = [str(item).strip().lower() for item in data if str(item).strip()]
        else:
            text = str(data).strip().lower()
            if not text:
                return None
            tokens = [token for token in text.replace('|', ' ').replace(',', ' ').split() if token]

        if not tokens:
            return None

        mapping = {
            'left': Qt.AlignmentFlag.AlignLeft,
            'right': Qt.AlignmentFlag.AlignRight,
            'top': Qt.AlignmentFlag.AlignTop,
            'bottom': Qt.AlignmentFlag.AlignBottom,
            'center': Qt.AlignmentFlag.AlignCenter,
            'hcenter': Qt.AlignmentFlag.AlignHCenter,
            'vcenter': Qt.AlignmentFlag.AlignVCenter,
            'middle': Qt.AlignmentFlag.AlignVCenter,
            'justify': Qt.AlignmentFlag.AlignJustify,
        }

        alignment = Qt.AlignmentFlag(0)
        for token in tokens:
            if token not in mapping:
                continue
            alignment |= mapping[token]

        return alignment if alignment != Qt.AlignmentFlag(0) else None

    def normalize_layout_justify(self, data: Any) -> str | None:
        if not isinstance(data, str):
            return None
        value = data.strip().lower()
        if value in {'start', 'center', 'end', 'space_between'}:
            return value
        return None

    def normalize_measure(self, data: Any) -> str | None:
        if data is None or isinstance(data, bool):
            return None
        if isinstance(data, (int, float)):
            return f'{int(round(data))}px'
        if isinstance(data, str):
            text = data.strip()
            if not text:
                return None
            try:
                return f'{int(round(float(text)))}px'
            except ValueError:
                pass
            return text
        return None

    def normalize_box_measure(self, data: Any) -> str | None:
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            value = int(round(data))
            return f'{value}px'

        if isinstance(data, str):
            raw_parts = [part for part in data.replace(',', ' ').split() if part]
            if not raw_parts:
                return None
            expanded = self._expand_box_sequence(raw_parts)
            if expanded is None:
                return None
            values = [self.normalize_measure(part) for part in expanded]
            if not all(isinstance(value, str) for value in values):
                return None
            top, right, bottom, left = values
            if top == right == bottom == left:
                return top
            return f'{top} {right} {bottom} {left}'

        if isinstance(data, dict):
            values = (
                self.normalize_measure(data.get('top')),
                self.normalize_measure(data.get('right')),
                self.normalize_measure(data.get('bottom')),
                self.normalize_measure(data.get('left')),
            )
            if all(isinstance(value, str) for value in values):
                top, right, bottom, left = values
                if top == right == bottom == left:
                    return top
                return f'{top} {right} {bottom} {left}'
            return None

        if isinstance(data, (list, tuple)):
            expanded = self._expand_box_sequence(list(data))
            if expanded is None:
                return None
            values = [self.normalize_measure(value) for value in expanded]
            if not all(isinstance(value, str) for value in values):
                return None
            top, right, bottom, left = values
            if top == right == bottom == left:
                return top
            return f'{top} {right} {bottom} {left}'

        return None

    def normalize_box_from_mapping(self, data: dict[str, Any], key: str) -> tuple[int, int, int, int] | None:
        box = self.normalize_box(data.get(key))
        side_values = {
            side: self.normalize_int(self._side_value(data, key, side))
            for side in ('top', 'right', 'bottom', 'left')
        }
        if all(value is None for value in side_values.values()):
            return box

        left, top, right, bottom = box or (0, 0, 0, 0)
        return (
            side_values['left'] if side_values['left'] is not None else left,
            side_values['top'] if side_values['top'] is not None else top,
            side_values['right'] if side_values['right'] is not None else right,
            side_values['bottom'] if side_values['bottom'] is not None else bottom,
        )

    def normalize_box_measure_from_mapping(self, data: dict[str, Any], key: str) -> str | None:
        box = self.normalize_box_from_mapping(data, key)
        if box is None:
            return None

        left, top, right, bottom = box
        if left == right == top == bottom:
            return f'{top}px'
        return f'{top}px {right}px {bottom}px {left}px'

    def normalize_box(self, data: Any) -> tuple[int, int, int, int] | None:
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            value = int(round(data))
            return value, value, value, value

        if isinstance(data, str):
            raw_parts = [part for part in data.replace(',', ' ').split() if part]
            if not raw_parts:
                return None
            expanded = self._expand_box_sequence(raw_parts)
            if expanded is None:
                return None
            values = tuple(self.normalize_int(part) for part in expanded)
            if all(isinstance(value, int) for value in values):
                top, right, bottom, left = values
                return left, top, right, bottom
            return None

        if isinstance(data, dict):
            values = (
                self.normalize_int(data.get('left')),
                self.normalize_int(data.get('top')),
                self.normalize_int(data.get('right')),
                self.normalize_int(data.get('bottom')),
            )
            if all(isinstance(value, int) for value in values):
                return values
            return None

        if isinstance(data, (list, tuple)):
            expanded = self._expand_box_sequence(list(data))
            if expanded is None:
                return None
            values = tuple(self.normalize_int(value) for value in expanded)
            if all(isinstance(value, int) for value in values):
                top, right, bottom, left = values
                return left, top, right, bottom

        return None

    def normalize_int(self, data: Any) -> int | None:
        if isinstance(data, bool):
            return None
        if isinstance(data, int):
            return data
        if isinstance(data, float):
            return int(round(data))
        if isinstance(data, str):
            value = data.strip().lower().removesuffix('px').strip()
            if not value:
                return None
            try:
                return int(round(float(value)))
            except ValueError:
                return None
        return None

    def _side_value(self, data: dict[str, Any], key: str, side: str) -> Any:
        return data.get(f'{key}-{side}', data.get(f'{key}_{side}'))

    def normalize_float(self, data: Any) -> float | None:
        if isinstance(data, bool):
            return None
        if isinstance(data, (int, float)):
            return float(data)
        if isinstance(data, str):
            value = data.strip().lower().removesuffix('px').strip()
            if not value:
                return None
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def normalize_shadow(self, data: Any) -> dict[str, Any] | None:
        if data is False or data is None:
            return None

        if isinstance(data, str):
            color = to_qcolor(data)
            if color is None:
                return None
            return {
                'color': color,
                'blur': 0.0,
                'offset': QPointF(0.0, 0.0),
            }

        if not isinstance(data, dict):
            return None

        if data.get('enabled') is False:
            return None

        color = to_qcolor(data.get('color', 'rgba(0, 0, 0, 0.35)'))
        if color is None:
            color = QColor(0, 0, 0, 90)

        blur = self.normalize_float(data.get('blur', data.get('radius', 0))) or 0.0
        x = self.normalize_float(data.get('x', data.get('offset_x', 0))) or 0.0
        y = self.normalize_float(data.get('y', data.get('offset_y', 0))) or 0.0

        offset_data = data.get('offset')
        if isinstance(offset_data, (list, tuple)) and len(offset_data) >= 2:
            x = self.normalize_float(offset_data[0]) or 0.0
            y = self.normalize_float(offset_data[1]) or 0.0
        elif isinstance(offset_data, dict):
            x = self.normalize_float(offset_data.get('x', offset_data.get('left', x))) or 0.0
            y = self.normalize_float(offset_data.get('y', offset_data.get('top', y))) or 0.0

        return {
            'color': color,
            'blur': max(0.0, blur),
            'offset': QPointF(x, y),
        }

    def _expand_box_sequence(self, values: list[Any]) -> tuple[Any, Any, Any, Any] | None:
        if not values:
            return None
        if len(values) == 1:
            top = right = bottom = left = values[0]
        elif len(values) == 2:
            top, right = values
            bottom, left = top, right
        elif len(values) == 3:
            top, right, bottom = values
            left = right
        elif len(values) == 4:
            top, right, bottom, left = values
        else:
            return None
        return top, right, bottom, left

    def clear_theme_helper_properties(self, widget: QWidget) -> None:
        for name in ('_themeBackgroundRule', '_themeBorderRule', '_themeBorderRadius', '_themePaddingRule', '_themePaddingBox'):
            if widget.property(name) is not None:
                widget.setProperty(name, None)
