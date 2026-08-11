import typing as t

from PySide6.QtCore import QByteArray, QObject

from src.utils.logging import logger


def _normalize_property_name(value: t.Any) -> str:
    if isinstance(value, QByteArray):
        return bytes(value.data()).decode('utf-8', errors='ignore')

    if isinstance(value, (bytes, bytearray)):
        return value.decode('utf-8', errors='ignore')

    return str(value)


def _format_property_value(value: t.Any) -> str | None:
    if isinstance(value, bool):
        return 'True' if value else 'False'

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return '""'

        if len(normalized) > 96:
            normalized = f'{normalized[:93]}...'
        return repr(normalized)

    if value is None:
        return 'None'

    return None


def _iter_custom_properties(obj: QObject) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for raw_name in obj.dynamicPropertyNames():
        name = _normalize_property_name(raw_name)
        if (
            not name
            or name == 'objectName'
            or name.startswith('_q_')
            or name.startswith('_PySide')
        ):
            continue

        formatted = _format_property_value(obj.property(name))
        if formatted is None:
            continue

        result.append((name, formatted))

    return result


def _count_object_tree_nodes(obj: QObject) -> int:
    total = 1
    for child in obj.children():
        total += _count_object_tree_nodes(child)
    return total


def _dump_object_tree_recursive(obj: QObject, *, indent: int) -> None:
    prefix = '  ' * indent
    logger.debug(f'{prefix}{obj.__class__.__name__}: {obj.objectName()}')

    for name, value in _iter_custom_properties(obj):
        logger.debug(f'{prefix}  {name}={value}')

    for child in obj.children():
        _dump_object_tree_recursive(child, indent=indent + 1)


def dump_object_tree(
    obj: QObject,
    indent: int = 0,
) -> None:
    total_nodes = _count_object_tree_nodes(obj)
    logger.debug(f'Object tree nodes: {total_nodes}')
    _dump_object_tree_recursive(obj, indent=indent)
