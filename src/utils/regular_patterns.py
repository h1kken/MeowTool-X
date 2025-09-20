from re import compile

COOKIE_PATTERN = compile(
    r'_\|(?:_|[^\s\r\n]*?\|_)\S{100,}'
)

STRING_100_PLUS_SYMBOLS = compile(
    r'\S{100,}'
)