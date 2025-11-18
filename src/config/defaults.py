from copy import deepcopy
from src.utils.other_utils import detect_system_locale


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
  'Debugger': {
    'Debug': False,
    'Info': False,
    'Warning': False,
    'Error': False,
    'Exception': False
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
      'Send Results To Discord Webhook': False
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
      'Main': {
        'Link': {'Enabled': False},
        'Country Registration': {'Enabled': False},
        'ID': {'Enabled': False},
        'Name': {'Enabled': False},
        'Display Name': {'Enabled': False},
        'Registration Date (DMY)': {'Enabled': False},
        'Registration Date (In Days)': {'Enabled': False},
        'Robux': {'Enabled': False},
        'Billing': {'Enabled': False},
        'Pending': {'Enabled': False},
        'Donate (1 Year)': {'Enabled': False},
        'Donate (All Time)': {
          'Enabled': False,
          'Max Page': -1
        },
        'Rap': {
          'Enabled': False,
          'Max Page': -1
        },
        'Card': {'Enabled': False},
        'Premium': {'Enabled': False},
        'Gamepasses': {
          'Enabled': False,
          'Max Page': -1,
          'Output Mode': 'Place (Names)'
        },
        'Custom Gamepasses': {
          'Enabled': False,
          'Max Page': -1,
          'Output Mode': 'Name (Number)',
          'Items': {
            'Fly A Pet Potion': {'Enabled': False},
            'Ride-A-Pet Potion': {'Enabled': False}
          }
        },
        'Badges': {
          'Enabled': False,
          'Max Page': -1,
          'Output Mode': 'Place (Names)'
        },
        'Favorite Places': {
          'Enabled': False,
          'Max Page': -1,
          'Output Mode': 'Names',
          'Items': {
            '920587237': {
              'Enabled': False,
              'Name': 'Adopt Me'
            },
            '142823291': {
              'Enabled': False,
              'Name': 'Murder Mystery 2'
            },
            '8737899170': {
              'Enabled': False,
              'Name': 'Pet Simulator 99'
            },
          }
        },
        'Bundles': {
          'Enabled': False,
          'Max Page': -1,
          'Output Mode': 'Names',
          'Items': {
            '192': {
              'Enabled': False,
              'Name': 'Korblox Deathspeaker'
            },
            '201': {
              'Enabled': False,
              'Name': 'Headless Horseman'
            }
          }
        },
        'Inventory Privacy': {'Enabled': False},
        'Trade Privacy': {'Enabled': False},
        'Can Trade': {'Enabled': False},
        'Sessions': {
          'Enabled': False,
          'Max Page': 1
        },
        'Email': {'Enabled': False},
        'Phone': {'Enabled': False},
        '2FA': {'Enabled': False},
        'Pin': {'Enabled': False},
        'Groups Owned': {
          'Enabled': False,
          'Output Mode': 'Names'
        },
        'Groups Members': {'Enabled': False},
        'Groups Pending': {'Enabled': False},
        'Groups Funds': {'Enabled': False},
        'Age Group': {'Enabled': False},
        'Verified Age': {'Enabled': False},
        'Verified Voice': {'Enabled': False},
        'Friends': {'Enabled': False},
        'Followers': {'Enabled': False},
        'Followings': {'Enabled': False},
        'Roblox Badges': {
          'Enabled': False,
          'Output Mode': 'Names'
        },
      },
      'Places': {},
      'Sorting': {
        'Enabled': False,
        'Categories': {}
      }
    },
    'Cookie Refresher': {
      'Break Old Cookies': False,
      'Single Mode': {
        'Cookie Save Mode': [1]
      },
      'Mass Mode': {
        'Cookie Save Mode': [1]
      }
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
      'Avoid Servers IDs': [],
      'Auto Retry': {
        'Enabled': False,
        'Retry After': 30,
      }
    }
  }
}


# Generating [Roblox > Cookie Checker > Sorting > Categories]
SORT_KEYS = {
  'Link': None,
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

def default_config():
    return deepcopy(DEFAULT_CONFIG)