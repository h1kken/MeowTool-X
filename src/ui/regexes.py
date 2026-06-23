import re

SIGNAL_NAME_PATTERN = re.compile(
    r'SignalInstance (\w+)\('
)

NORMALIZE_QT_KEY_PATTERN = re.compile(
    r'[^a-zA-Z0-9_]'
)


__all__ = [name for name in globals() if name.isupper()]
