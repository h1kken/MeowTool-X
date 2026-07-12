import random
from urllib.parse import quote

from src.services.roblox.constants import ROBLOX_AGE_GROUP_KEYMAP
from src.services.roblox.regexes import ROBLOX_AGE_GROUP_PATTERN
from src.utils.logging import logger


def convert_age_group(string: str) -> str:
    match = ROBLOX_AGE_GROUP_PATTERN.search(string)
    if not match:
        logger.warning(f'Can\'t convert age: {string}')
        return 'UNK'

    direction, age_from, age_to = match.groups()
    return f'{age_from}{f'-{age_to}' if age_to else ''}{ROBLOX_AGE_GROUP_KEYMAP.get(str(direction).lower(), '')}'


def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))


def encode_string_to_url(string: str) -> str:
    return quote(string)
