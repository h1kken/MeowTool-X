import math
import random
from pathlib import Path
import locale
from datetime import datetime
from urllib.parse import quote

def create_needed_folders_and_files():
    PATHS = [
        ('Proxy', 'Checker', 'proxies.txt'),
        ('Roblox', 'proxies.txt'),
        ('Roblox', 'Cookie Sorter'),
        ('Roblox', 'Cookie Checker', 'cookies.txt'),
        ('Roblox', 'Cookie Refresher', 'Mass Mode', 'cookies.txt'),
        ('Roblox', 'Transaction Analysis', 'cookies.txt'),
        ('Roblox', 'Time Booster', 'cookies.txt')
    ]

    for args in PATHS:
        path = Path(*args)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix and not path.exists():
            path.touch(exist_ok=True)

def get_nested(data: dict, key: str, *, sep='.', default=None):
    keys = key.split(sep)
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def set_nested(data: dict, key: str, value, *, sep='.'):
    keys = key.split(sep)
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_files_from_folder(*path_args: str, only_files: bool = True) -> list[str]:
    path = Path(*path_args)
    
    if not (path.exists() or path.is_dir()):
        return []

    return [p.name for p in path.iterdir() if p.is_file() or not only_files]

def detect_system_locale() -> str:
    system_locale = locale.getlocale()[0].lower()
    if 'russia' in system_locale:
        return 'ru'
    else:
        return 'en'

def current_time_in_ms() -> int:
    return math.floor((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)

def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))

async def convert_date(input_date: str, output_format: str):
    DATE_FORMATS = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ'
    ]

    for date_format in DATE_FORMATS:
        try:
            date_formatted = datetime.strptime(input_date, date_format)
            return date_formatted.strftime(output_format)
        except ValueError:
            continue
        
def encode_string_to_url(string: str) -> str:
    return quote(string)