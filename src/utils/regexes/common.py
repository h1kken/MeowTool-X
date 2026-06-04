import re

FILENAME_SPECIAL_CHARS_PATTERN = re.compile(
    r'[\\/*?:"<>|]'
)
