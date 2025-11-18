import os
from typing import Literal
import locale

def cls() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')

def detect_system_locale() -> Literal['RU', 'EN']:
    system_locale = locale.getlocale()[0].lower()
    if 'russia' in system_locale:
        return 'RU'
    else:
        return 'EN'