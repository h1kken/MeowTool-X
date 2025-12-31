import random
import re
import emoji
from urllib.parse import quote
from src.utils.regex import FILENAME_SPECIAL_CHARS_PATTERN, ROBLOX_AGE_GROUP_PATTERN
from src.utils.consts import ROBLOX_AGE_GROUP_MAPPING
from src.utils.logger import logger


def convert_age_group(string: str) -> str:
    match = ROBLOX_AGE_GROUP_PATTERN.search(string)
    if not match:
        logger.warning(f'Can\'t convert age: {string}')
        return 'UNK'
    
    direction, ageFrom, ageTo = match.groups()
    return f'{ageFrom}{f'-{ageTo}' if ageTo else ''}{ROBLOX_AGE_GROUP_MAPPING.get(str(direction).lower(), '')}'

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
    return re.sub(FILENAME_SPECIAL_CHARS_PATTERN, replace, string)

def remove_emojies(string: str, *, replace: str = ' ') -> str:
    return emoji.replace_emoji(string, replace=replace)

def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))

def encode_string_to_url(string: str) -> str:
    return quote(string)