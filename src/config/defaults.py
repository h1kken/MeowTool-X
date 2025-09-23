from copy import deepcopy

DEFAULT_CONFIG_LOADER = {
    'Loader': {
        'Config_On_Launch': 'default'
    },
    'Saver': {
        'Auto_Save': False
    },
    'MeowTool': {
        'Username': '',
        'First_Launch': True
    }
}

def default_config_loader():
    return deepcopy(DEFAULT_CONFIG_LOADER)

DEFAULT_CONFIG = {
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
    }
}

def default_config():
    return deepcopy(DEFAULT_CONFIG)