from src.utils.logging import logger
from PySide6.QtCore import QObject, QEvent


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


def dump_object_tree(obj: QObject, indent: int = 0):
    obj_name = obj.objectName() or '<no name>'
    logger.debug('  ' * indent + f'{obj.__class__.__name__}: {obj_name}')

    for child in obj.children():
        dump_object_tree(child, indent + 1)
