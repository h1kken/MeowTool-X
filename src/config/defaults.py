from copy import deepcopy

from src.utils.constants import DEFAULT_THEME, SYSTEM_LOCALE


DEFAULT_CONFIG_LOADER = {
  "Loader": {
    "Config On Load": "default",
    "Developer Mode": False
  },
  "Saver": {
    "Auto Save Config Changes": False,
    "Auto Save Theme Changes": False
  },
  "Updater": {
    "Check Updates": True,
    "Save Old Versions": True
  },
  "Misc": {
    "Debugger": {
      "Debug": False,
      "Info": False,
      "Warning": False,
      "Error": False,
      "Exception": False,
    },
  },
  "MeowTool": {
    "First Launch": True,
    "Username": ""
  },
}


def default_config_loader():
    return deepcopy(DEFAULT_CONFIG_LOADER)


DEFAULT_CONFIG = {
  "General": {
    "Language": SYSTEM_LOCALE,
    "Theme": DEFAULT_THEME.stem,
    "Disable Warnings For Links": False,
    "Disable Warnings For Dangerous Actions": False,
  },
  "Theme": {
    "Autoload Selected Theme": True,
  },
  "Misc": {
    "Rainbow Mode": {
      "Enabled": False,
      "Cycle Duration": 5000,
      "Palette": "Pastel",
    }
  },
  "HTTP Engine": {
    "Concurrency Profile": "Auto",
    "Max Concurrency": 64,
    "Per Proxy Max In Flight": 8,
    "Direct Max In Flight": 2,
  },
  "Outputs": {
    "Play Sound When Work Finished": False,
    "Telegram Bot": {
      "Token": "",
      "Chat ID": "",
      "Send Results To Telegram Bot": False,
    },
    "Discord Webhook": {
      "URL": "",
      "Send Results To Discord Webhook": False
    },
    "Discord Rich Presence": False
  },
  "Proxy": {
    "Checker": {
      "Main Threads": (50, 1, 1000),
      "Maximum Wait Response": (10, 1, 60),
      "Save Good In Custom File": False,
      "Save Without Protocol": False,
    }
  },
  "Roblox": {
    "General": {
      "Add Symbols Between Warning And Cookie": False,
      "Symbols Between Warning And Cookie": "CAEaAhAB.",
      "Proxy": {
        "Use Proxy": False,
        "Auto Protocol If Not Specified": "http"
      },
    },
    "Cookie Sorter": {"Output Filename": "output"},
    "Cookie Checker": {
      "Firstly Check For Valid": False,
      "Valid Threads": (50, 1, 1000),
      "Main Threads": (25, 1, 100),
      "Output Filename Like Input": False,
      "Output Filename": "output",
      "Move Cookie To The Next Line": False,
      "Main": {
        "Link": {"Enabled": False},
        "ID": {"Enabled": False},
        "Name": {"Enabled": False},
        "Display Name": {"Enabled": False},
        "Country Registration": {"Enabled": False},
        "Registration Date (DMY)": {"Enabled": False},
        "Registration Date (In Days)": {"Enabled": False},
        "Robux": {"Enabled": False},
        "Billing": {"Enabled": False},
        "Pending": {"Enabled": False},
        "Donate (1 Period)": {"Enabled": False},
        "Donate (All Time)": {
          "Enabled": False,
          "Max Page": -1
        },
        "Rap": {
          "Enabled": False,
          "Max Page": -1
        },
        "Card": {"Enabled": False},
        "Premium": {"Enabled": False},
        "Gamepasses": {
          "Enabled": False,
          "Max Page": -1,
          "Output Mode": "Place (Names)",
        },
        "Custom Gamepasses": {
          "Enabled": False,
          "Max Page": -1,
          "Output Mode": "Name (Number)",
          "Items": {
            "Fly A Pet Potion": {"Enabled": False},
            "Ride-A-Pet Potion": {"Enabled": False},
          },
        },
        "Badges": {
          "Enabled": False,
          "Max Page": -1,
          "Output Mode": "Place (Names)",
        },
        "Favorite Places": {
          "Enabled": False,
          "Max Page": -1,
          "Output Mode": "Names",
          "Items": {},
        },
        "Bundles": {
          "Enabled": False,
          "Max Page": -1,
          "Output Mode": "Names",
          "Items": {},
        },
        "Inventory Privacy": {"Enabled": False},
        "Trade Privacy": {"Enabled": False},
        "Can Trade": {"Enabled": False},
        "Sessions": {
          "Enabled": False,
          "Max Page": 1
        },
        "Email": {"Enabled": False},
        "Phone": {"Enabled": False},
        "2FA": {"Enabled": False},
        "Pin": {"Enabled": False},
        "Groups Owned": {
          "Enabled": False,
          "Output Mode": "Names"
        },
        "Groups Members": {"Enabled": False},
        "Groups Pending": {"Enabled": False},
        "Groups Funds": {"Enabled": False},
        "Age Group": {"Enabled": False},
        "Verified Age": {"Enabled": False},
        "Verified Voice": {"Enabled": False},
        "Friends": {"Enabled": False},
        "Followers": {"Enabled": False},
        "Followings": {"Enabled": False},
        "Roblox Badges": {
          "Enabled": False,
          "Output Mode": "Names"
        },
      },
      "Sorting": {
        "Enabled": False,
        "Categories": {}
      },
      "Places": {},
    },
    "Cookie Refresher": {
      "Break Old Cookies": False,
      "Cookie Save Mode": [1]
    },
    "Transaction Analysis": {
      "Firstly Check For Valid": False,
      "Valid Threads": (50, 1, 1000),
      "Main Threads": (25, 1, 250),
      "Indent By The Longest Name": False,
    },
  },
}


# Generating [Roblox > Cookie Checker > Sorting > Categories]
SORT_KEYS = {
  "Link": None,
  "ID": str,
  "Name": str,
  "Display Name": str,
  "Country Registration": str,
  "Registration Date (DMY)": str,
  "Registration Date (In Days)": int,
  "Robux": int,
  "Billing": int,
  "Pending": int,
  "Donate (1 Year)": int,
  "Donate (All Time)": int,
  "Rap": int,
  "Card": int,
  "Premium": str,
  "Gamepasses": int,
  "Custom Gamepasses": int,
  "Badges": int,
  "Favorite Places": int,
  "Bundles": int,
  "Inventory Privacy": str,
  "Trade Privacy": str,
  "Can Trade": str,
  "Sessions": int,
  "Email": str,
  "Phone": str,
  "2FA": str,
  "Pin": str,
  "Groups Owned": int,
  "Groups Members": int,
  "Groups Pending": int,
  "Groups Funds": int,
  "Age Group": str,
  "Verified Age": str,
  "Verified Voice": str,
  "Friends": int,
  "Followers": int,
  "Followings": int,
  "Roblox Badges": int,
}

SORT_KEYS_NAMES = (
  "Gamepasses",
  "Badges",
  "Custom Gamepasses",
  "Favorite Places",
  "Bundles",
  "Groups Owned",
  "Roblox Badges",
)

SORT_KEYS_PLACES = (
  "Gamepasses",
  "Badges"
)

for key_name, key_type in SORT_KEYS.items():
    if key_type is str:
        DEFAULT_CONFIG["Roblox"]["Cookie Checker"]["Sorting"]["Categories"][key_name] = {
          "Enabled": False,
          "Options": {
            "Yes": True,
            "No": False
          },
        }
    
    if key_type is int:
        DEFAULT_CONFIG["Roblox"]["Cookie Checker"]["Sorting"]["Categories"][key_name] = {
          "Enabled": False,
          "Options": {
            "Zero": False,
            "From": {
              "Enabled": False,
              "Items": {}
            },
            "From To": {
              "Enabled": False,
              "Items": {}
            },
          },
        }

for key_name in SORT_KEYS_NAMES:
    DEFAULT_CONFIG["Roblox"]["Cookie Checker"]["Sorting"]["Categories"][key_name]["Names"] = False

for key_name in SORT_KEYS_PLACES:
    DEFAULT_CONFIG["Roblox"]["Cookie Checker"]["Sorting"]["Categories"][key_name]["Places"] = False


def default_config():
    return deepcopy(DEFAULT_CONFIG)
