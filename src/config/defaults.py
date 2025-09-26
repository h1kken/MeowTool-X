from copy import deepcopy

DEFAULT_CONFIG_LOADER = {
  'loader': {
    'config_on_launch': 'default'
  },
  'saver': {
    'auto_save': False
  },
  'updater': {
    'check_updates': True,
    'save_old_versions': True
  },
  'meowtool': {
    'first_launch': True,
    'username': ''
  }
}

def default_config_loader():
    return deepcopy(DEFAULT_CONFIG_LOADER)

DEFAULT_CONFIG = {
  'general': {
    'language': 'ru_RU',
    'program_name': 'MeowTool... Meow :3',
    'disable_warnings_for_links': False,
    'disable_warnings_for_dangerous_actions': False
  },
  'outputs': {
    'play_sound_when_work_finished': False,
    'telegram_bot': {
      'token': '',
      'chat_id': '',
      'send_results_to_telegram_bot': False
    },
    'discord_webhook': {
      'url': '',
      'send_results_to_discord_webhook': False
    }
  },
  'proxy': {
    'checker': {
      'number_of_threads_for_checker': (50, 1, 1000),
      'timeout': (10, 1, 60),
      'save_good_in_custom_file': False,
      'save_without_protocol': False
    }
  },
  'roblox': {
    'general': {
      'add_symbols_between_warning_and_cookie': False,
      'symbols_between_warning_and_cookie': 'CAEaAhAB.',
      'proxy': {
        'use_proxy': False,
        'auto_protocol_if_not_specified': 'http'
      }
    },
    'cookie_sorter': {
      'output_filename': 'output'
    },
    'cookie_checker': {
      'firstly_check_for_valid': False,
      'number_of_threads_for_valid_checker': (50, 1, 1000),
      'number_of_threads_for_main_checker': (25, 1, 100),
      'name_output_file_the_same_as_input_file': False,
      'output_filename': 'output',
      'move_cookie_to_the_next_line': False,
      'main': {},
      'sorting': {
        'enabled': False,
        'categories': {}
      }
    },
    'cookie_refresher': {
      'break_old_cookies': False,
      'single_mode': {
        'cookie_save_mode': [1]
      },
      'mass_mode': {
        'cookie_save_mode': [1]
      }
    },
    'transaction_analysis': {
      'first_check_all_cookies_for_valid': False,
      'number_of_threads_for_valid_checker': (50, 1, 1000),
      'number_of_threads_for_transaction_analysis': (25, 1, 250),
      'indent_by_the_longest_name': False
    },
    'time_booster': {
      'maximum_launchers': 10,
      'minimum_age_in_days': 0,
      'auto_retry': True,
      'auto_retry_time': 30,
      'random_server_id': True,
      'server_id': '',
      'avoid_servers_ids': []
    },
    'misc': {
      'gamepasses_parser': {
        'remove_emojies_from_name': False,
        'remove_round_brackets_and_in_from_name': False,
        'remove_square_brackets_and_in_from_name': False
      },
      'badges_parser': {
        'remove_emojies_from_name': False,
        'remove_round_brackets_and_in_from_name': False,
        'remove_square_brackets_and_in_from_name': False
      }
    }
  }
}

# Generating [roblox.cookie_checker.main]
MAIN_KEYS = [
    'link',
    'country_registration',
    'id',
    'name',
    'display_name',
    'registration_date_dmy',
    'registration_date_in_days',
    'robux',
    'billing',
    'pending',
    'donate_1_year',
    'donate_all_time',
    'rap',
    'card',
    'premium',
    'gamepasses',
    'custom_gamepasses',
    'badges',
    'favorite_places',
    'bundles',
    'inventory_privacy',
    'trade_privacy',
    'can_trade',
    'sessions',
    'email',
    'phone',
    '2fa',
    'pin',
    'groups_owned',
    'groups_members',
    'groups_pending',
    'groups_funds',
    'age_group',
    'verified_age',
    'verified_voice',
    'friends',
    'followers',
    'followings',
    'roblox_badges'
]
for key in MAIN_KEYS:
    DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key] = {'enabled': False}

    if key in ('donate_all_time', 'rap', 'gamepasses', 'badges', 'custom_gamepasses', 'favorite_places', 'bundles'):
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['max_page'] = -1

    if key in ('gamepasses', 'badges'):
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['output_mode'] = 'PlaceNames'
    elif key == 'custom_gamepasses':
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['output_mode'] = 'NameNumber'
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['items'] = {
          custom_gamepass_name: {
            'enabled': False
          } for custom_gamepass_name in [
              'Fly A Pet Potion',
              'Ride-A-Pet Potion'
          ]
        }
    elif key in ('favorite_places', 'bundles', 'groups_owned', 'roblox_badges'):
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['output_mode'] = 'Names'
        if key == 'favorite_places':
            DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['items'] = {
              favorite_place_id: {
                'enabled': False,
                'name': favorite_place_name
              } for favorite_place_id, favorite_place_name in [
                  ('920587237', 'Adopt Me'),
                  ('142823291', 'Murder Mystery 2'),
                  ('8737899170', 'Pet Simulator 99')
              ]
            }
        elif key == 'bundles':
            DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['items'] = {
              bundle_id: {
                'enabled': False,
                'name': bundle_name
              } for bundle_id, bundle_name in [
                  ('192', 'Korblox Deathspeaker'),
                  ('201', 'Headless Horseman')
              ]
            }
    elif key == 'sessions':
        DEFAULT_CONFIG['roblox']['cookie_checker']['main'][key]['max_page'] = 1
    
# Generating [roblox.cookie_checker.sorting]
SORT_KEYS = {
    'country_registration': str,
    'id': str,
    'name': str,
    'display_name': str,
    'registration_date_dmy': str,
    'registration_date_in_days': int,
    'robux': int,
    'billing': int,
    'pending': int,
    'donate_1_year': int,
    'donate_all_time': int,
    'rap': int,
    'card': int,
    'premium': str,
    'gamepasses': int,
    'custom_gamepasses': int,
    'badges': int,
    'favorite_places': int,
    'bundles': int,
    'inventory_privacy': str,
    'trade_privacy': str,
    'can_trade': str,
    'sessions': int,
    'email': str,
    'phone': str,
    '2fa': str,
    'pin': str,
    'groups_owned': int,
    'groups_members': int,
    'groups_pending': int,
    'groups_funds': int,
    'age_group': str,
    'verified_age': str,
    'verified_voice': str,
    'friends': int,
    'followers': int,
    'followings': int,
    'roblox_badges': int
}
for key, type in SORT_KEYS.items():
    if type == str:
        DEFAULT_CONFIG['roblox']['cookie_checker']['sorting']['categories'][key] = {
          'enabled': False,
          'options': {
            'positive': {'enabled': True},
            'negative': {'enabled': True}
          }
        }
    elif type == int:
        DEFAULT_CONFIG['roblox']['cookie_checker']['sorting']['categories'][key] = {
          'enabled': False,
          'options': {
            'zero': {'enabled': False},
            'from': {
              'enabled': False,
              'items': []
            },
            'from_to': {
              'enabled': False,
              'items': []
            }
          }
        }

        if key in ('gamepasses', 'badges', 'custom_gamepasses', 'favorite_places', 'bundles', 'groups_owned', 'roblox_badges'):
            DEFAULT_CONFIG['roblox']['cookie_checker']['sorting']['categories'][key]['names'] = False
            if key in ('gamepasses', 'badges'):
              DEFAULT_CONFIG['roblox']['cookie_checker']['sorting']['categories'][key]['places'] = False

# Generating [roblox.cookie_refresher]
REFRESHER_KEYS = [
  'single',
  'mass'
]
for key in REFRESHER_KEYS:
  DEFAULT_CONFIG['roblox']['cookie_refresher'][f'{key}_mode'] = {
    'cookie_save_mode': [1]
  }

def default_config():
    return deepcopy(DEFAULT_CONFIG)