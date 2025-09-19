import os
import json
from pathlib import Path
from utils.logger import logger
from utils.helpers import get_nested, set_nested, get_files_from_folder
from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject):
    # config_loaded = pyqtSignal()
    
    def __init__(self, filename: str = 'default'):
        super().__init__()
        self._path = Path('Settings', 'Configs', f'{filename}.json')
        self.load(filename)
    
    def _default_settings(self):
        return {
            'General': {
                'Language': 'RU',
                'Program_Name': 'MeowTool... Meow :3',
                'Disable_Warnings_For_Links': False,
                'Disable_Warnings_For_Dangerous_Actions': False,
            },
            'Outputs': {
                'Play_Sound_At_The_End_Of_The_Work': False,
                'Telegram_Bot': {
                    'Token': '',
                    'Chat_ID': '',
                    'Send_Results_To_Telegram_Bot': False
                },
                'Discord_Webhook': {
                    'URL': '',
                    'Send_Results_To_Discord_Webhook': False
                }
            },
            'Proxy': {
                'Checker': {
                    'Number_Of_Threads_For_Checker': 50,
                    'Timeout': 10,
                    'Save_Good_In_Custom_File': False,
                    'Save_Without_Protocol': False
                }
            },
            'Roblox': {
                'General': {
                    'Symbols_Between_Warning_And_Cookie': 'CAEaAhAB.',
                    'Add_Symbols_Between_Warning_And_Cookie': False,
                    'Proxy': {
                        'Use_Proxy': False,
                        'Auto_Protocol_If_Not_Specified': 'http'
                    }
                },
                'Cookie_Sorter': {
                    'Output_Filename': 'output'
                },
                'Cookie_Checker': {
                    'First_Check_All_Cookies_For_Valid': False,
                    'Number_Of_Threads_For_Valid_Checker': 50,
                    'Number_Of_Threads_For_Main_Checker': 25,
                    'Name_Output_File_The_Same_As_Input_File': False,
                    'Output_Filename': 'output',
                    'Move_Cookie_To_The_Next_Line': False,
                    'Sorting': {
                        'Sort': False,
                        # Not finished
                    },
                    'Main': {
                        # Not finished
                    }
                },
                'Cookie_Refresher': {
                    'Break_Old_Cookies': False,
                    'Single_Mode': {
                        'Cookie_Save_Mode': [1]
                    },
                    'Mass_Mode': {
                        'Cookie_Save_Mode': [1]
                    }
                },
                'Transaction_Analysis': {
                    'General': {
                        'First_Check_All_Cookies_For_Valid': False,
                        'Number_Of_Threads_For_Valid_Checker': 50,
                        'Number_Of_Threads_For_Transaction_Analysis': 20,
                        'Indentation_By_The_Longest_Name': False
                    }
                },
                'Misc': {
                    'Gamepasses_Parser': {
                        'Remove_Emojies_From_Name': False,
                        'Remove_Round_Brackets_And_In_From_Name': False,
                        'Remove_Square_Brackets_And_In_From_Name': False
                    },
                    'Badges_Parser': {
                        'Remove_Emojies_From_Name': False,
                        'Remove_Round_Brackets_And_In_From_Name': False,
                        'Remove_Square_Brackets_And_In_From_Name': False
                    }
                }
            },
        }

#     config['Roblox']['CookieChecker'].add('Sorting', table())
#     config['Roblox']['CookieChecker']['Sorting']['Sort'] = False
#     config['Roblox']['CookieChecker']['Sorting'].add(comment('Categories'))
#     for category in cookieData.listOfCookieData:
#         if category[3] is int:
#             config['Roblox']['CookieChecker']['Sorting'][category[1]] = [False, False, [False, []], [False, []]]
#         elif category[3] is str:
#             config['Roblox']['CookieChecker']['Sorting'][category[1]] = False

#         match category[1]:
#             case 'Gamepasses' | 'Badges':
#                 config['Roblox']['CookieChecker']['Sorting'][f'{category[1]}_Names'] = False
#                 config['Roblox']['CookieChecker']['Sorting'][f'{category[1]}_Places'] = False
#             case 'Custom_Gamepasses' | 'Favorite_Places' | 'Bundles' | 'Groups_Owned' | 'Roblox_Badges':
#                 config['Roblox']['CookieChecker']['Sorting'][f'{category[1]}_Names'] = False

#     # Roblox > Cookie Checker > Main
#     config['Roblox']['CookieChecker'].add('Main', table())
#     for data in cookieData.listOfCookieData:
#         config['Roblox']['CookieChecker']['Main'][data[1]] = False

#         if data[1] in ('Donate_All_Time', 'Rap', 'Gamepasses', 'Badges', 'Custom_Gamepasses', 'Favorite_Places', 'Bundles'):
#             config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Max_Check_Pages'] = -1
#             config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Max_Check_Pages'].comment('-1 - All')

#         match data[1]:
#             case 'Gamepasses' | 'Badges':
#                 config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Output_Mode'] = 'PlaceNames'
#                 config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Output_Mode'].comment('Options: [ Number | Names | PlaceNumber | PlaceNames ]')
#             case 'Custom_Gamepasses':
#                 config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses_Output_Mode'] = 'NameNumber'
#                 config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses_Output_Mode'].comment('Options: [ Number | NameNumber ]')
#                 config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses_List'] = [
#                     ['Fly A Pet Potion',  False],
#                     ['Ride-A-Pet Potion', False]
#                 ]
#             case 'Favorite_Places' | 'Bundles' | 'Groups_Owned' | 'Roblox_Badges':
#                 config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Output_Mode'] = 'Names'
#                 config['Roblox']['CookieChecker']['Main'][f'{data[1]}_Output_Mode'].comment('Options: [ Number | Names ]')
#                 match data[1]:
#                     case 'Favorite_Places':
#                         config['Roblox']['CookieChecker']['Main']['Favorite_Places_List'] = [
#                             [920587237,  'Adopt Me',         False],
#                             [142823291,  'Murder Mystery 2', False],
#                             [8737899170, 'Pet Simulator 99', False]
#                         ]
#                     case 'Bundles':
#                         config['Roblox']['CookieChecker']['Main']['Bundles_List'] = [
#                             [192, 'Korblox Deathspeaker', False],
#                             [201, 'Headless Horseman',    False]
#                         ]
#             case 'Sessions':
#                 config['Roblox']['CookieChecker']['Main']['Sessions_Max_Check_Pages'] = 1
#                 config['Roblox']['CookieChecker']['Main']['Sessions_Max_Check_Pages'].comment('-1 - All, 1 - Must be good to avoid long wait for this \'https://imgur.com/a/TrBIdCu\'')

#     # Roblox > Cookie Checker > Places
#     config['Roblox']['CookieChecker'].add('Places', table())
#     for place in listOfPlaces:
#         config['Roblox']['CookieChecker']['Places'][place.placeNames[1]] = False
    
#     # Roblox > Cookie Checker > Places > Gamepasses and Badges
#     for place in listOfPlaces:
#         placeName = place.__name__
#         config['Roblox']['CookieChecker'].add(placeName, table())
#         if getattr(place, 'Gamepasses', False):
#             config['Roblox']['CookieChecker'][placeName].add(comment('Gamepasses'))
#             for gamepass in place.Gamepasses.listOfGamepasses:
#                 config['Roblox']['CookieChecker'][placeName][gamepass[2]] = False
#         if getattr(place, 'Badges', False):
#             config['Roblox']['CookieChecker'][placeName].add(comment('Badges'))
#             for badge in place.Badges.listOfBadges:
#                 config['Roblox']['CookieChecker'][placeName][badge[2]] = False

    def _validate(self):
        ...
    
    def create(self, filename: str):
        if (self._path.parent / f'{filename}.json').exists():
            return
        
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(f'{self._path.parent / filename}.json', 'w', encoding='utf-8') as f:
            json.dump(self._default_settings(), f, indent=2, ensure_ascii=False)
    
    def load(self, filename: str = 'default'):
        self._path = Path('Settings', 'Configs', f'{filename}.json')
        
        try:
            if not self._path.exists() or filename == '.Loader':
                logger.warning('Config not found. Using default...')
                raise FileNotFoundError

            with open(self._path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            self._data = self._default_settings()
            self.save()
        
    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        
    def delete(self, filename: str):
        if self._path.exists():
            os.remove(self._path)
            if self._path.stem == filename or not get_files_from_folder('Settings', 'Configs'):
                self.load('default')
                
    def get(self, key, *, sep='.', default=None):
        return get_nested(self._data, key, sep=sep, default=default)
        
    def set(self, key, value, *, sep='.'):
        set_nested(self._data, key, value, sep=sep)