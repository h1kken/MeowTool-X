import os
import sys
import locale
from pathlib import Path


# MeowTool
VERSION = 'v1.0.0'
PROGRAM_NAME = 'MeowTool X'

# window
WINDOW_X = 900
WINDOW_Y = 500

# special chars
PROGRAM_NAME_CHARS = {'<', '>', '|', '^', '&'}
FILENAME_CHARS = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}

# start paths
START_PATHS = [ # TODO: All-In-One
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

# date formats
DATE_FORMAT = '%d.%m.%Y'
DATE_TIME_FORMAT = '%d.%m.%Y %H:%M:%S'

# system paths
ROOT = Path(sys._MEIPASS).resolve() if getattr(sys, '_MEIPASS', None) else Path(__file__).resolve().parents[2]
LOCAL_APPDATA = Path(os.environ['LOCALAPPDATA'])
SYSTEM_DRIVE = Path(os.environ['SystemDrive'])

# system locale
SYSTEM_LOCALE = 'RU' if str(locale.getlocale()[0]).lower().startswith('ru') else 'EN'

# translation paths
PATH_TRANSLATIONS_USER = ROOT / 'Settings' / 'Translations'
PATH_TRANSLATIONS_SOURCE = ROOT / 'src' / 'translation' / 'translations'

# roblox paths
PATH_FISHSTRAP = LOCAL_APPDATA / 'Fishstrap' / 'Fishstrap.exe'
PATH_BLOXSTRAP = LOCAL_APPDATA / 'Bloxstrap' / 'Bloxstrap.exe'
PATH_ROBLOXPLAYERBETA = SYSTEM_DRIVE / 'Program Files (x86)' / 'Roblox' / 'Versions'

# roblox account functions | TODO
TIME_FRAME_TRANSACTIONS = 'Year'
ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME = 100
ITEMS_PER_PAGE_RAP = 100
ITEMS_PER_PAGE_GAMEPASSES = 100
ITEMS_PER_PAGE_FAVORITE_PLACES = 100
ITEMS_PER_PAGE_BUNDLES = 100
ITEMS_PER_PAGE_PLACE_SERVER_IDS = 50
BADGES_COUNT_LIMIT = 100

# roblox
ROBLOX_COOKIE_START = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_'
ROBLOX_REG_DATE_FORMAT = '%d.%m.%Y'
ROBLOX_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%SZ'
]
ROBLOX_AGE_GROUP_MAPPING = {
    'over'  : '+',
    'under' : '-'
}
ROBLOX_PRIVACY_MAPPING = {
    'AllUsers'                     : 'Everyone',
    'FriendsFollowingAndFollowers' : 'Friends & Followings & Followers',
    'FriendsAndFollowing'          : 'Friends & Followings',
    'Friends'                      : 'Friends',
    'NoOne'                        : 'No One'
}

COUNTRY_CODES = {
    'AF': 'Afghanistan',
    'AL': 'Albania',
    'DZ': 'Algeria',
    'AS': 'American Samoa',
    'AD': 'Andorra',
    'AO': 'Angola',
    'AI': 'Anguilla',
    'AQ': 'Antarctica',
    'AG': 'Antigua and Barbuda',
    'AR': 'Argentina',
    'AM': 'Armenia',
    'AW': 'Aruba',
    'AU': 'Australia',
    'AT': 'Austria',
    'AZ': 'Azerbaijan',
    'BS': 'Bahamas',
    'BH': 'Bahrain',
    'BD': 'Bangladesh',
    'BB': 'Barbados',
    'BY': 'Belarus',
    'BE': 'Belgium',
    'BZ': 'Belize',
    'BJ': 'Benin',
    'BM': 'Bermuda',
    'BT': 'Bhutan',
    'BO': 'Bolivia (Plurinational State of)',
    'BQ': 'Bonaire, Sint Eustatius and Saba',
    'BA': 'Bosnia and Herzegovina',
    'BW': 'Botswana',
    'BV': 'Bouvet Island',
    'BR': 'Brazil',
    'IO': 'British Indian Ocean Territory',
    'BN': 'Brunei Darussalam',
    'BG': 'Bulgaria',
    'BF': 'Burkina Faso',
    'BI': 'Burundi',
    'CV': 'Cabo Verde',
    'KH': 'Cambodia',
    'CM': 'Cameroon',
    'CA': 'Canada',
    'KY': 'Cayman Islands',
    'CF': 'Central African Republic',
    'TD': 'Chad',
    'CL': 'Chile',
    'CN': 'China',
    'CX': 'Christmas Island',
    'CC': 'Cocos (Keeling) Islands',
    'CO': 'Colombia',
    'KM': 'Comoros',
    'CD': 'Congo (the Democratic Republic of the)',
    'CG': 'Congo',
    'CK': 'Cook Islands',
    'CR': 'Costa Rica',
    'HR': 'Croatia',
    'CU': 'Cuba',
    'CW': 'Curaçao',
    'CY': 'Cyprus',
    'CZ': 'Czechia',
    'CI': 'Côte d\'Ivoire',
    'DK': 'Denmark',
    'DJ': 'Djibouti',
    'DM': 'Dominica',
    'DO': 'Dominican Republic',
    'EC': 'Ecuador',
    'EG': 'Egypt',
    'SV': 'El Salvador',
    'GQ': 'Equatorial Guinea',
    'ER': 'Eritrea',
    'EE': 'Estonia',
    'SZ': 'Eswatini',
    'ET': 'Ethiopia',
    'FK': 'Falkland Islands [Malvinas]',
    'FO': 'Faroe Islands',
    'FJ': 'Fiji',
    'FI': 'Finland',
    'FR': 'France',
    'GF': 'French Guiana',
    'PF': 'French Polynesia',
    'TF': 'French Southern Territories',
    'GA': 'Gabon',
    'GM': 'Gambia',
    'GE': 'Georgia',
    'DE': 'Germany',
    'GH': 'Ghana',
    'GI': 'Gibraltar',
    'GR': 'Greece',
    'GL': 'Greenland',
    'GD': 'Grenada',
    'GP': 'Guadeloupe',
    'GU': 'Guam',
    'GT': 'Guatemala',
    'GG': 'Guernsey',
    'GN': 'Guinea',
    'GW': 'Guinea-Bissau',
    'GY': 'Guyana',
    'HT': 'Haiti',
    'HM': 'Heard Island and McDonald Islands',
    'VA': 'Holy See',
    'HN': 'Honduras',
    'HK': 'Hong Kong',
    'HU': 'Hungary',
    'IS': 'Iceland',
    'IN': 'India',
    'ID': 'Indonesia',
    'IR': 'Iran (Islamic Republic of)',
    'IQ': 'Iraq',
    'IE': 'Ireland',
    'IM': 'Isle of Man',
    'IL': 'Israel',
    'IT': 'Italy',
    'JM': 'Jamaica',
    'JE': 'Jersey',
    'JO': 'Jordan',
    'KZ': 'Kazakhstan',
    'KE': 'Kenya',
    'KI': 'Kiribati',
    'KP': 'Korea (the Democratic People\'s Republic of)',
    'KR': 'Korea (the Republic of)',
    'KW': 'Kuwait',
    'KG': 'Kyrgyzstan',
    'LA': 'Lao People\'s Democratic Republic',
    'LV': 'Latvia',
    'LB': 'Lebanon',
    'LS': 'Lesotho',
    'LR': 'Liberia',
    'LY': 'Libya',
    'LI': 'Liechtenstein',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'MO': 'Macao',
    'MG': 'Madagascar',
    'MW': 'Malawi',
    'MY': 'Malaysia',
    'MV': 'Maldives',
    'ML': 'Mali',
    'MT': 'Malta',
    'MH': 'Marshall Islands',
    'MQ': 'Martinique',
    'MR': 'Mauritania',
    'MU': 'Mauritius',
    'YT': 'Mayotte',
    'MX': 'Mexico',
    'FM': 'Micronesia (Federated States of)',
    'MD': 'Moldova (the Republic of)',
    'MC': 'Monaco',
    'MN': 'Mongolia',
    'ME': 'Montenegro',
    'MS': 'Montserrat',
    'MA': 'Morocco',
    'MZ': 'Mozambique',
    'MM': 'Myanmar',
    'NA': 'Namibia',
    'NR': 'Nauru',
    'NP': 'Nepal',
    'NL': 'Netherlands',
    'NC': 'New Caledonia',
    'NZ': 'New Zealand',
    'NI': 'Nicaragua',
    'NE': 'Niger',
    'NG': 'Nigeria',
    'NU': 'Niue',
    'NF': 'Norfolk Island',
    'MP': 'Northern Mariana Islands',
    'NO': 'Norway',
    'OM': 'Oman',
    'PK': 'Pakistan',
    'PW': 'Palau',
    'PS': 'Palestine, State of',
    'PA': 'Panama',
    'PG': 'Papua New Guinea',
    'PY': 'Paraguay',
    'PE': 'Peru',
    'PH': 'Philippines',
    'PN': 'Pitcairn',
    'PL': 'Poland',
    'PT': 'Portugal',
    'PR': 'Puerto Rico',
    'QA': 'Qatar',
    'MK': 'Republic of North Macedonia',
    'RO': 'Romania',
    'RU': 'Russian Federation',
    'RW': 'Rwanda',
    'RE': 'Réunion',
    'BL': 'Saint Barthélemy',
    'SH': 'Saint Helena, Ascension and Tristan da Cunha',
    'KN': 'Saint Kitts and Nevis',
    'LC': 'Saint Lucia',
    'MF': 'Saint Martin (French part)',
    'PM': 'Saint Pierre and Miquelon',
    'VC': 'Saint Vincent and the Grenadines',
    'WS': 'Samoa',
    'SM': 'San Marino',
    'ST': 'Sao Tome and Principe',
    'SA': 'Saudi Arabia',
    'SN': 'Senegal',
    'RS': 'Serbia',
    'SC': 'Seychelles',
    'SL': 'Sierra Leone',
    'SG': 'Singapore',
    'SX': 'Sint Maarten (Dutch part)',
    'SK': 'Slovakia',
    'SI': 'Slovenia',
    'SB': 'Solomon Islands',
    'SO': 'Somalia',
    'ZA': 'South Africa',
    'GS': 'South Georgia and the South Sandwich Islands',
    'SS': 'South Sudan',
    'ES': 'Spain',
    'LK': 'Sri Lanka',
    'SD': 'Sudan',
    'SR': 'Suriname',
    'SJ': 'Svalbard and Jan Mayen',
    'SE': 'Sweden',
    'CH': 'Switzerland',
    'SY': 'Syrian Arab Republic',
    'TW': 'Taiwan (Province of China)',
    'TJ': 'Tajikistan',
    'TZ': 'Tanzania, United Republic of',
    'TH': 'Thailand',
    'TL': 'Timor-Leste',
    'TG': 'Togo',
    'TK': 'Tokelau',
    'TO': 'Tonga',
    'TT': 'Trinidad and Tobago',
    'TN': 'Tunisia',
    'TR': 'Turkey',
    'TM': 'Turkmenistan',
    'TC': 'Turks and Caicos Islands',
    'TV': 'Tuvalu',
    'UG': 'Uganda',
    'UA': 'Ukraine',
    'AE': 'United Arab Emirates',
    'GB': 'United Kingdom of Great Britain and Northern Ireland',
    'UM': 'United States Minor Outlying Islands',
    'US': 'United States of America',
    'UY': 'Uruguay',
    'UZ': 'Uzbekistan',
    'VU': 'Vanuatu',
    'VE': 'Venezuela (Bolivarian Republic of)',
    'VN': 'Viet Nam',
    'VG': 'Virgin Islands (British)',
    'VI': 'Virgin Islands (U.S.)',
    'WF': 'Wallis and Futuna',
    'EH': 'Western Sahara',
    'YE': 'Yemen',
    'ZM': 'Zambia',
    'ZW': 'Zimbabwe',
    'AX': 'Åland Islands',
}

# config paths
PATH_CONFIGS = ROOT / 'Settings' / 'Configs'

# config
CONFIG_COMMENT_SYMBOLS = ('!', '#')

# logger
DATE_LOGGER_FORMAT = '%d.%m.%Y %H.%M.%S'

# database keymaps
DATABASE_ROBLOX_COOKIE_CHECKER_KEYMAP = {
    
}

# http
HTTP_CLIENT_MAX_RETRIES = 5

# other
IS_LAUNCHED_WITH_CONSOLE = sys.stdout.isatty()