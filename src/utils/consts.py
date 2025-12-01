import os
import sys
import locale
from pathlib import Path


# start paths
START_PATHS = [
    Path('Proxy', 'Checker', 'proxies.txt'),
    Path('Roblox', 'proxies.txt'),
    Path('Roblox', 'Cookie Sorter'),
    Path('Roblox', 'Cookie Checker', 'cookies.txt'),
    # Path('Roblox', 'LogPass Checker', 'LogPasses.txt'),
    # Path('Roblox', 'Game Checker', 'cookies.txt'),
    Path('Roblox', 'Cookie Refresher', 'Mass Mode', 'cookies.txt'),
    Path('Roblox', 'Transaction Analysis', 'cookies.txt'),
    # Path('Roblox', 'Time Booster', 'cookies.txt'),
    # Path('Roblox', 'Robux Transfer', 'cookies.txt)
]

# root path
ROOT = Path(sys._MEIPASS).resolve() if getattr(sys, '_MEIPASS', None) else Path(__file__).resolve().parents[2]

# system locale
SYSTEM_LOCALE = 'RU' if str(locale.getlocale()[0]).lower().startswith('ru') else 'EN'

# translation paths
PATH_TRANSLATIONS_USER = ROOT / 'Settings' / 'Translations'
PATH_TRANSLATIONS_SOURCE = ROOT / 'src' / 'translation' / 'translations'

# roblox paths
PATH_FISHSTRAP = Path(os.path.expandvars(r'%LOCALAPPDATA%\Fishstrap\Fishstrap.exe'))
PATH_BLOXSTRAP = Path(os.path.expandvars(r'%LOCALAPPDATA%\Bloxstrap\Bloxstrap.exe'))
PATH_ROBLOXPLAYERBETA = Path(rf'{os.environ['SystemDrive']}\Program Files (x86)\Roblox\Versions')

# roblox account functions | TODO: WONT TO BE HERE
TIME_FRAME_TRANSACTIONS = 'Year'
ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME = 100
ITEMS_PER_PAGE_RAP = 100
ITEMS_PER_PAGE_GAMEPASSES = 100
ITEMS_PER_PAGE_BADGES = 100
ITEMS_PER_PAGE_FAVORITE_PLACES = 100
ITEMS_PER_PAGE_BUNDLES = 100
ITEMS_PER_PAGE_PLACE_SERVER_IDS = 50

# config paths
PATH_CONFIGS = ROOT / 'Settings' / 'Configs'

# config
CONFIG_COMMENT_SYMBOLS = ('!', '#')

# date formats
DATE_LOGGER_FORMAT = '%d.%m.%Y %H.%M.%S'
DATE_ROBLOX_REG_DATE_FORMAT = '%d.%m.%Y'
DATE_ROBLOX_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%SZ'
]

# database keymaps
DATABASE_ROBLOX_COOKIE_CHECKER_KEYMAP = {
    
}

# http client
HTTP_CLIENT_MAX_RETRIES = 5

# other
IS_LAUNCHED_IN_CONSOLE = sys.stdout.isatty()