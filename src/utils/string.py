import ast
import random
import re
from typing import Any
from urllib.parse import quote

import emoji

from src.utils.constants import ROBLOX_AGE_GROUP_KEYMAP
from src.utils.logging import logger
from src.utils.regexes import FILENAME_SPECIAL_CHARS_PATTERN, ROBLOX_AGE_GROUP_PATTERN


def convert_age_group(string: str) -> str:
    match = ROBLOX_AGE_GROUP_PATTERN.search(string)
    if not match:
        logger.warning(f'Can\'t convert age: {string}')
        return 'UNK'
    
    direction, age_from, age_to = match.groups()
    return f'{age_from}{f'-{age_to}' if age_to else ''}{ROBLOX_AGE_GROUP_KEYMAP.get(str(direction).lower(), '')}'


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


def safe_literal_eval(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))


def encode_string_to_url(string: str) -> str:
    return quote(string)
