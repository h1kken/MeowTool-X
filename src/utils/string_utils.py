import random
from re import sub
from emoji import replace_emoji
from urllib.parse import quote
from src.utils.regex_utils import FILENAME_SPECIAL_CHARS_PATTERN, ROBLOX_AGE_GROUP_PATTERN
from typing import Literal
from src.utils.logger import logger


def convert_age_group(string: str) -> str:
    match = ROBLOX_AGE_GROUP_PATTERN.search(string)
    if not match:
        logger.warning(f'< [CONVERT_AGE_GROUP] > Can\'t convert age: {string}')
        return 'UNK'
    
    direction, age, checked = match.groups()
    return f'{age}{'+' if direction.lower() == 'over' else '-'}{' (Checked)' if checked else ''}'

def format_duration(ms: int, *, sep: str = '. ', end: str = '.', out_units: Literal['d', 'h', 'm', 's', 'ms', 'all'] = 'all') -> str:
    s, ms = divmod(ms, 1000)
    m, s  = divmod(s,  60)
    h, m  = divmod(m,  60)
    d, h  = divmod(h,  24)
    units = {'d': d, 'h': h, 'm': m, 's': s, 'ms': ms}
    
    parts = []
    for key, value in units.items():
        if (value or parts) and (key in out_units or 'all' in out_units):
            parts.append(f'{value}{...}')

    return f'{sep.join(parts)}{end}'

def remove_brackets_and_in(string: str, *, round: bool = True, square: bool = True) -> str:
    new_string = ''
    skip = 0
    for char in string:
        if char == '(' and round or char == '[' and square:
            skip += 1
        elif skip > 0 and (char == ')' and round or char == ']' and square):
            skip -= 1
        elif skip == 0:
            new_string += char
    return new_string

def remove_filename_special_chars(string: str, *, replace: str = '') -> str:
    return sub(FILENAME_SPECIAL_CHARS_PATTERN, replace, string)

def remove_emojies(string: str, *, replace: str = ' ') -> str:
    return replace_emoji(string, replace=replace)

def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))

def encode_string_to_url(string: str) -> str:
    return quote(string)