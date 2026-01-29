import re


ROBLOX_COOKIE_PATTERN = re.compile(
    r'_\|(?:_|[^\s\r\n]*\|_)\S{100,}'
)

ROBLOX_VERSION_PATH_PATTERN = re.compile(
    r'version-.+'
)

ROBLOX_AGE_GROUP_PATTERN = re.compile(
    r'(?i)(Over|Under)?(\d+)[^\d]*(\d+)?'
)

STRING_100_PLUS_SYMBOLS_PATTERN = re.compile(
    r'\S{100,}'
)

FILENAME_SPECIAL_CHARS_PATTERN = re.compile(
    r'[\\/*?:"<>|]'
)

SIGNAL_NAME_PATTERN = re.compile(
    r'SignalInstance (\w+)\('
)

PROXY_PROTOCOL_PATTERN = re.compile(
    r'(?i)^(https?|socks[45])'
)

PROXY_PROTOCOL_IP_PORT_USER_PASS_PATTERN = re.compile(
    r'(?i)^(?:(?P<protocol>https?|socks[45])://)?'
    r'(?P<ip>[^:]+):'
    r'(?P<port>\d{1,5}):'
    r'(?P<username>[^:]+):'
    r'(?P<password>.+)$'
)

PROXY_PROTOCOL_USER_PASS_IP_PORT_PATTERN = re.compile(
    r'(?i)^(?:(?P<protocol>https?|socks[45])://)?'
    r'(?P<username>[^:@]+):'
    r'(?P<password>[^:@]+)@'
    r'(?P<ip>[^:]+):'
    r'(?P<port>\d{1,5})$'
)

PROXY_PROTOCOL_IP_PORT_PATTERN = re.compile(
    r'(?i)^(?:(?P<protocol>https?|socks[45])://)?'
    r'(?P<ip>[^:]+):'
    r'(?P<port>\d{1,5})$'
)

NORMALIZE_QT_KEY_PATTERN = re.compile(
    r'[^a-zA-Z0-9_]'
)
