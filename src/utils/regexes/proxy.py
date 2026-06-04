import re

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
