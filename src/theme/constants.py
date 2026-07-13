from PySide6.QtCore import QEvent

EVENT_ACTIONS = {
    QEvent.Type.Enter: 'hover',
    QEvent.Type.Leave: 'leave',
    QEvent.Type.MouseButtonPress: 'press',
    QEvent.Type.MouseButtonRelease: 'release',
    QEvent.Type.Wheel: 'wheel',
    QEvent.Type.FocusIn: 'focus',
    QEvent.Type.FocusOut: 'blur',
}

__all__ = [name for name in globals() if name.isupper()]
