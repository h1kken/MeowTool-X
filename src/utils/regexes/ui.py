import re

SIGNAL_NAME_PATTERN = re.compile(
    r'SignalInstance (\w+)\('
)

NORMALIZE_QT_KEY_PATTERN = re.compile(
    r'[^a-zA-Z0-9_]'
)

QSS_TARGET_PATTERN = re.compile(
    r'(?P<base>[a-zA-Z_*][\w*]*)'
    r'(?P<props>(?:\[\s*\w+\s*=\s*(?:"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\]]+)\s*\])*)'
)

QSS_TARGET_PROPERTY_PATTERN = re.compile(
    r'\[\s*(?P<key>\w+)\s*=\s*(?P<value>"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\]]+)\s*\]'
)

CUBIC_BEZIER_PATTERN = re.compile(
    r'cubic-bezier\s*\(([^)]+)\)',
    re.IGNORECASE,
)


__all__ = [name for name in globals() if name.isupper()]
