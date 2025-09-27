import os
import random
from typing import Literal
import locale

def cls() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')

def detect_system_locale() -> Literal['ru', 'en']:
    system_locale = locale.getlocale()[0].lower()
    if 'russia' in system_locale:
        return 'ru'
    else:
        return 'en'

def generate_browser_tracker_id() -> str:
    return str(random.randint(100000, 175000)) + str(random.randint(100000, 900000))