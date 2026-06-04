from typing import Callable

from PySide6.QtCore import QByteArray, QEvent, QObject

from src.utils.logging import logger


class EventListener(QObject):
    BLACKLIST = {
        QEvent.Type.Paint,
        QEvent.Type.UpdateRequest,
        QEvent.Type.LayoutRequest,
        QEvent.Type.Timer,
        QEvent.Type.Polish,
        QEvent.Type.StyleChange,
        QEvent.Type.FontChange,
        QEvent.Type.Resize,
        QEvent.Type.Move,
        QEvent.Type.ChildAdded,
        QEvent.Type.ChildRemoved,
        QEvent.Type.MouseMove,
        QEvent.Type.HoverMove,
        QEvent.Type.NonClientAreaMouseMove,
        QEvent.Type.NonClientAreaMouseButtonPress,
        QEvent.Type.NonClientAreaMouseButtonRelease,
        QEvent.Type.WindowDeactivate,
        QEvent.Type.Enter,
        QEvent.Type.Leave,
        QEvent.Type.HoverEnter,
        QEvent.Type.HoverLeave,
        QEvent.Type.Expose,
    }
    
    def eventFilter(self, obj, event: QEvent):
        if event.type() in self.BLACKLIST:
            return False
        
        logger.debug(f'[EVENT] {obj.__class__.__name__:<20} {event.type().name}')
        return False


def _normalize_property_name(value) -> str:
    if isinstance(value, QByteArray):
        return bytes(value).decode('utf-8', errors='ignore')

    if isinstance(value, (bytes, bytearray)):
        return value.decode('utf-8', errors='ignore')

    return str(value)


def _format_property_value(value) -> str | None:
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


def _dump_object_tree_recursive(
    obj: QObject,
    *,
    indent: int,
    total_nodes: int,
    state: dict[str, int],
    progress_callback: Callable[[int, int, QObject], None] | None = None,
) -> None:
    state['visited'] += 1
    if callable(progress_callback):
        progress_callback(state['visited'], total_nodes, obj)
    prefix = '  ' * indent
    obj_name = obj.objectName() or '<no name>'
    logger.debug(prefix + f'{obj.__class__.__name__}: {obj_name}')

    for name, value in _iter_custom_properties(obj):
        logger.debug(prefix + f'  {name}={value}')

    for child in obj.children():
        _dump_object_tree_recursive(
            child,
            indent=indent + 1,
            total_nodes=total_nodes,
            state=state,
            progress_callback=progress_callback,
        )


def dump_object_tree(
    obj: QObject,
    indent: int = 0,
    *,
    progress_callback: Callable[[int, int, QObject], None] | None = None,
):
    total_nodes = _count_object_tree_nodes(obj)
    logger.debug(f'Object tree nodes: {total_nodes}')
    _dump_object_tree_recursive(
        obj,
        indent=indent,
        total_nodes=total_nodes,
        state={'visited': 0},
        progress_callback=progress_callback,
    )
