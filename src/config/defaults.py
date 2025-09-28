from copy import deepcopy
from ..utils.other_utils import detect_system_locale

DEFAULT_CONFIG_LOADER = {
  'Loader': {
    'Config On Launch': 'default'
  },
  'Saver': {
    'Auto Save Changes': False
  },
  'Updater': {
    'Check Updates': True,
    'Save Old Versions': True
  },
  'MeowTool': {
    'First Launch': True,
    'Username': ''
  }
}

def default_config_loader():
    return deepcopy(DEFAULT_CONFIG_LOADER)

DEFAULT_CONFIG = {
  'General': {
    'Language': detect_system_locale(),
    'Program Name': 'MeowTool... Meow :3',
    'Disable Warnings For Links': False,
    'Disable Warnings For Dangerous Actions': False
  },
  'Outputs': {
    'Play Sound When Work Finished': False,
    'Telegram Bot': {
      'Token': '',
      'Chat ID': '',
      'Send Results To Telegram Bot': False
    },
    'Discord Webhook': {
      'URL': '',
      'Wend Results To Discord Webhook': False
    }
  },
  'Proxy': {
    'Checker': {
      'Main Threads': (50, 1, 1000),
      'Maximum Wait Response': (10, 1, 60),
      'Save Good In Custom File': False,
      'Save Without Protocol': False
    }
  },
  'Roblox': {
    'General': {
      'Add Symbols Between Warning And Cookie': False,
      'Symbols Between Warning And Cookie': 'CAEaAhAB.',
      'Proxy': {
        'Use Proxy': False,
        'Auto Protocol If Not Specified': 'http'
      }
    },
    'Cookie Sorter': {
      'Output Filename': 'output'
    },
    'Cookie Checker': {
      'Firstly Check For Valid': False,
      'Valid Threads': (50, 1, 1000),
      'Main Threads': (25, 1, 100),
      'Output Filename Like Input': False,
      'Output Filename': 'output',
      'Move Cookie To The Next Line': False,
      'Main': {},
      'Places': {},
      'Sorting': {
        'Enabled': False,
        'Categories': {}
      }
    },
    'Cookie Refresher': {
      'Break Old Cookies': False,
    },
    'Transaction Analysis': {
      'Firstly Check For Valid': False,
      'Valid Threads': (50, 1, 1000),
      'Main Threads': (25, 1, 250),
      'Indent By The Longest Name': False
    },
    'Time Booster': {
      'Maximum Launchers': 10,
      'Minimum Days After Registration': 0,
      'Random Server ID': True,
      'Force Server ID': '',
      'Avoid Servers IDs': {},
      'Auto Retry': {
        'Enabled': False,
        'Retry After Seconds': 30,
      }
    },
    'Misc': {}
  }
}

# Generating [Roblox > Cookie Checker > Main]
MAIN_KEYS = [
    'Link',
    'Country Registration',
    'ID',
    'Name',
    'Display Name',
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
    'Roblox Badges'
]
for key in MAIN_KEYS:
    DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key] = {'Enabled': False}

    if key in ('Donate (All Time)', 'Rap', 'Gamepasses', 'Badges', 'Custom Gamepasses', 'Favorite Places', 'Bundles'):
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Max Page'] = -1

    if key in ('Gamepasses', 'Badges'):
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Output Mode'] = 'Place (Names)'
    elif key == 'Custom Gamepasses':
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Output Mode'] = 'Name (Number)'
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Items'] = {
          custom_gamepass_name: {
            'Enabled': False
          } for custom_gamepass_name in [
              'Fly A Pet Potion',
              'Ride-A-Pet Potion'
          ]
        }
    elif key in ('Favorite Places', 'Bundles', 'Groups Owned', 'Roblox Badges'):
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Output Mode'] = 'Names'
        if key == 'Favorite Places':
            DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Items'] = {
              favorite_place_id: {
                'Enabled': False,
                'Name': favorite_place_name
              } for favorite_place_id, favorite_place_name in [
                  ('920587237', 'Adopt Me'),
                  ('142823291', 'Murder Mystery 2'),
                  ('8737899170', 'Pet Simulator 99')
              ]
            }
        elif key == 'Bundles':
            DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Items'] = {
              bundle_id: {
                'Enabled': False,
                'Name': bundle_name
              } for bundle_id, bundle_name in [
                  ('192', 'Korblox Deathspeaker'),
                  ('201', 'Headless Horseman')
              ]
            }
    elif key == 'Sessions':
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Main'][key]['Max Page'] = 1
    
# Generating [Roblox > Cookie Checker > Sorting > Categories]
SORT_KEYS = {
    'Country Registration': str,
    'ID': str,
    'Name': str,
    'Display Name': str,
    'Registration Date (DMY)': str,
    'Registration Date (In Days)': int,
    'Robux': int,
    'Billing': int,
    'Pending': int,
    'Donate (1 Year)': int,
    'Donate (All Time)': int,
    'Rap': int,
    'Card': int,
    'Premium': str,
    'Gamepasses': int,
    'Custom Gamepasses': int,
    'Badges': int,
    'Favorite Places': int,
    'Bundles': int,
    'Inventory Privacy': str,
    'Trade Privacy': str,
    'Can Trade': str,
    'Sessions': int,
    'Email': str,
    'Phone': str,
    '2FA': str,
    'Pin': str,
    'Groups Owned': int,
    'Groups Members': int,
    'Groups Pending': int,
    'Groups Funds': int,
    'Age Group': str,
    'Verified Age': str,
    'Verified Voice': str,
    'Friends': int,
    'Followers': int,
    'Followings': int,
    'Roblox Badges': int
}
for key, key_type in SORT_KEYS.items():
    if key_type == str:
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Sorting']['Categories'][key] = {
          'Enabled': False,
          'Options': {
            'Positives': True,
            'Negatives': True
          }
        }
    elif key_type == int:
        DEFAULT_CONFIG['Roblox']['Cookie Checker']['Sorting']['Categories'][key] = {
          'Enabled': False,
          'Options': {
            'Zero': False,
            'From': {
              'Enabled': False,
              'Items': {}
            },
            'From To': {
              'Enabled': False,
              'Items': {}
            }
          }
        }

        if key in ('Gamepasses', 'Badges', 'Custom Gamepasses', 'Favorite Places', 'Bundles', 'Groups Owned', 'Roblox Badges'):
            DEFAULT_CONFIG['Roblox']['Cookie Checker']['Sorting']['Categories'][key]['Names'] = False
            if key in ('Gamepasses', 'Badges'):
              DEFAULT_CONFIG['Roblox']['Cookie Checker']['Sorting']['Categories'][key]['Places'] = False

# Generating [Roblox > Cookie Refresher > Single Mode & Mass Mode]
REFRESHER_KEYS = [
  'Single Mode',
  'Mass Mode'
]
for key in REFRESHER_KEYS:
  DEFAULT_CONFIG['Roblox']['Cookie Refresher'][key] = {
    'Cookie Save Mode': [1]
  }

# Generating [Misc > Gamepasses Parser & Badges Parser]
MISC_KEYS = {'Gamepasses Parser', 'Badges Parser'}
for key in MISC_KEYS:
  DEFAULT_CONFIG['Roblox']['Misc'][key] = {
    'Removes From Name': {
      'Emojies': False,
      'Round Brackets And In': False,
      'Square Brackets And In': False
    }
  }

def default_config():
    return deepcopy(DEFAULT_CONFIG)