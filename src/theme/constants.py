from PySide6.QtCore import QEvent

GRADIENT_DIRECTIONS = {
    'vertical':   (0, 0, 0, 1),
    'horizontal': (0, 0, 1, 0),
    'diagonal':   (0, 0, 1, 1),
    'inverse':    (1, 0, 0, 1),
}

EVENT_ACTIONS = {
    QEvent.Type.Enter: 'hover',
    QEvent.Type.Leave: 'leave',
    QEvent.Type.MouseButtonPress: 'press',
    QEvent.Type.MouseButtonRelease: 'release',
    QEvent.Type.Wheel: 'wheel',
    QEvent.Type.FocusIn: 'focus',
    QEvent.Type.FocusOut: 'blur',
}

SUPPORTED_BG_MEDIA_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.bmp', '.gif',
    '.webp', '.svg', '.ico', '.mp4', '.webm',
    '.avi', '.mov', '.mkv',
}

THEME_AUTOLOAD_FALLBACK = True
THEME_RUNTIME_RAINBOW_ENABLED_FALLBACK = False
THEME_RUNTIME_RAINBOW_DURATION_FALLBACK = 5000
THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK = 'Pastel'


__all__ = [name for name in globals() if name.isupper()]
