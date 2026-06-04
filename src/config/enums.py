from enum import StrEnum


# CONFIG LOADER
class ConfigLoaderKey(StrEnum):
    LOADER_PATH = "Loader"
    LOADER_CONFIG_ON_LOAD = f"{LOADER_PATH}>Config On Load"
    LOADER_DEVELOPER_MODE = f"{LOADER_PATH}>Developer Mode"

    SAVER_PATH = "Saver"
    SAVER_AUTO_SAVE_CONFIG_CHANGES = f"{SAVER_PATH}>Auto Save Config Changes"
    SAVER_AUTO_SAVE_THEME_CHANGES = f"{SAVER_PATH}>Auto Save Theme Changes"

    UPDATER_PATH = "Updater"
    UPDATER_CHECK_UPDATES = f"{UPDATER_PATH}>Check Updates"
    UPDATER_SAVE_OLD_VERSION = f"{UPDATER_PATH}>Save Old Versions"
    
    MISC_PATH = "Misc"
    MISC_DEBUGGER_PATH = f"{MISC_PATH}>Debugger"
    MISC_DEBUGGER_DEBUG = f"{MISC_DEBUGGER_PATH}>Debug"
    MISC_DEBUGGER_INFO = f"{MISC_DEBUGGER_PATH}>Info"
    MISC_DEBUGGER_WARNING = f"{MISC_DEBUGGER_PATH}>Warning"
    MISC_DEBUGGER_ERROR = f"{MISC_DEBUGGER_PATH}>Error"
    MISC_DEBUGGER_EXCEPTION = f"{MISC_DEBUGGER_PATH}>Exception"

    MEOWTOOL_PATH = "MeowTool"
    MEOWTOOL_FIRST_LAUNCH = f"{MEOWTOOL_PATH}>First Launch"
    MEOWTOOL_USERNAME = f"{MEOWTOOL_PATH}>Username"


# CONFIG
class ConfigKey(StrEnum):
    ...