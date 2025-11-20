import re

# roblox
COOKIE_PATTERN = re.compile(
    r'_\|(?:_|[^\s\r\n]*?\|_)\S{100,}'
)

ROBLOX_VERSION_PATH_PATTERN = re.compile(
    r'version-.+'
)

STRING_100_PLUS_SYMBOLS_PATTERN = re.compile(
    r'\S{100,}'
)

FILENAME_SPECIAL_CHARS_PATTERN = re.compile(
    r'[\\/*?:"<>|]'
)