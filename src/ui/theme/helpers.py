from __future__ import annotations

import typing as t

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from .constants import SIDES

if t.TYPE_CHECKING:
    from src.core.types import DataMap


def resolve_qt_target(root: QWidget, target: str) -> list[QObject]:
    target = target.strip()
    
    if '#' in target:
        class_name, object_name = target.split('#', 1)
        
        class_name = class_name.strip() or None
        object_name = object_name.strip() or None
    else:
        class_name = target
        object_name = None

    if not object_name:
        return []

    objects = root.findChildren(QObject, object_name)

    if class_name is None:
        return objects

    return [obj for obj in objects if obj.inherits(class_name)]


def parse_sides(styles: DataMap, *, property_name: str) -> list[str]:
    rules: list[str] = []
    
    for side in SIDES:
        value = styles.get(side)
        
        if value is None:
            continue
        
        rules.append(f'{property_name}-{side}: {value};')
    
    return rules


def parse_box_values(styles: DataMap, *, property_name: str) -> tuple[int, int, int, int]:
    values: list[int] = [0, 0, 0, 0] # top right bottom left

    raw = styles.get(property_name)
    
    if isinstance(raw, str):
        raw = raw.split()

    match raw:
        
        case int() | float():
            values = [int(raw)] * 4

        case list():
            match len(raw):
                
                case 1:
                    number = to_int(raw[0])
                    if number is not None:
                        values = [number] * 4

                case 2:
                    numbers = list(map(to_int, (raw[0], raw[1])))
                    if all_ints(numbers):
                        values = numbers * 2

                case 3:
                    numbers = list(map(to_int, (raw[0], raw[1], raw[2], raw[1])))
                    if all_ints(numbers):
                        values = numbers

                case 4:
                    numbers = list(map(to_int, raw))
                    if all_ints(numbers):
                        values = numbers

                case _:
                    pass

        case dict():
            for index, side in enumerate(SIDES):
                if side in raw:
                    number = to_int(raw[side])
                    if number is not None:
                        values[index] = number

        case _:
            pass

    for index, side in enumerate(SIDES):
        key = f'{property_name}-{side}'
        if key in styles:
            number = to_int(styles[key])
            if number is not None:
                values[index] = number

    return values[0], values[1], values[2], values[3]


def to_int(value: object) -> int | None:
    match value:
        case int():
            return value

        case float():
            return int(value)

        case str():
            try:
                return int(value.strip())
            except ValueError:
                return None

        case _:
            return None


def all_ints(values: list[int | None]) -> t.TypeGuard[list[int]]:
    return all(value is not None for value in values)
