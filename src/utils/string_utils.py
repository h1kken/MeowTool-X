from re import sub
from emoji import replace_emoji
from urllib.parse import quote
from .regex_utils import FILENAME_SPECIAL_CHARS

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
    return sub(FILENAME_SPECIAL_CHARS, replace, string)

def remove_emojies(string: str, *, replace: str = ' ') -> str:
    return replace_emoji(string, replace=replace)

def encode_string_to_url(string: str) -> str:
    return quote(string)