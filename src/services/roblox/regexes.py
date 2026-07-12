import re

ROBLOX_COOKIE_PATTERN = re.compile(
    r'_\|(?:_|[^\s\r\n]*\|_)\S{100,}'
)

ROBLOX_COOKIE_PATTERN_BYTES = re.compile(
    ROBLOX_COOKIE_PATTERN.pattern.encode('ascii')
)

ROBLOX_VERSION_PATH_PATTERN = re.compile(
    r'version-.+'
)

ROBLOX_AGE_GROUP_PATTERN = re.compile(
    r'(Over|Under)?(\d+)[^\d]*(\d+)?',
    re.IGNORECASE,
)

STRING_100_PLUS_SYMBOLS_PATTERN = re.compile(
    r'\S{100,}'
)

STRING_100_PLUS_SYMBOLS_PATTERN_BYTES = re.compile(
    STRING_100_PLUS_SYMBOLS_PATTERN.pattern.encode('ascii')
)


__all__ = [name for name in globals() if name.isupper()]
