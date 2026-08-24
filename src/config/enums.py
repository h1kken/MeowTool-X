from enum import StrEnum


# CONFIG LOADER
class ConfigLoaderKey(StrEnum):
    # Loader
    LOADER_PATH           = 'Loader'
    LOADER_CONFIG_ON_LOAD = f'{LOADER_PATH}>Config On Load'
    LOADER_DEVELOPER_MODE = f'{LOADER_PATH}>Developer Mode'

    # Saver
    SAVER_PATH                     = 'Saver'
    SAVER_AUTO_SAVE_CONFIG_CHANGES = f'{SAVER_PATH}>Auto Save Config Changes'

    # Updater
    UPDATER_PATH          = 'Updater'
    UPDATER_CHECK_UPDATES = f'{UPDATER_PATH}>Check Updates'
    
    # Misc
    MISC_PATH = 'Misc'
    
    # Misc > Debugger
    MISC_DEBUGGER_PATH      = f'{MISC_PATH}>Debugger'
    MISC_DEBUGGER_DEBUG     = f'{MISC_DEBUGGER_PATH}>Debug'
    MISC_DEBUGGER_INFO      = f'{MISC_DEBUGGER_PATH}>Info'
    MISC_DEBUGGER_WARNING   = f'{MISC_DEBUGGER_PATH}>Warning'
    MISC_DEBUGGER_ERROR     = f'{MISC_DEBUGGER_PATH}>Error'
    MISC_DEBUGGER_EXCEPTION = f'{MISC_DEBUGGER_PATH}>Exception'

    # MeowTool
    MEOWTOOL_PATH         = 'MeowTool'
    MEOWTOOL_FIRST_LAUNCH = f'{MEOWTOOL_PATH}>First Launch'
    MEOWTOOL_USERNAME     = f'{MEOWTOOL_PATH}>Username'


# CONFIG
class ConfigKey(StrEnum):
    # General
    GENERAL_PATH     = 'General'
    GENERAL_LANGUAGE = f'{GENERAL_PATH}>Language'
    GENERAL_THEME    = f'{GENERAL_PATH}>Theme'
    
    # Outputs
    OUTPUTS_PATH                      = 'Outputs'
    OUTPUTS_TELEGRAM_BOT_PATH         = f'{OUTPUTS_PATH}>Telegram Bot'
    OUTPUTS_TELEGRAM_BOT_TOKEN        = f'{OUTPUTS_TELEGRAM_BOT_PATH}>Token'
    OUTPUTS_TELEGRAM_BOT_CHAT_ID      = f'{OUTPUTS_TELEGRAM_BOT_PATH}>Chat ID'
    OUTPUTS_TELEGRAM_BOT_SEND_RESULTS = f'{OUTPUTS_TELEGRAM_BOT_PATH}>Send Results'

    OUTPUTS_DISCORD_WEBHOOK_PATH         = f'{OUTPUTS_PATH}>Discord Webhook'
    OUTPUTS_DISCORD_WEBHOOK_URL          = f'{OUTPUTS_DISCORD_WEBHOOK_PATH}>URL'
    OUTPUTS_DISCORD_WEBHOOK_SEND_RESULTS = f'{OUTPUTS_DISCORD_WEBHOOK_PATH}>Send Results'
    
    # Proxy
    PROXY_PATH = 'Proxy'
    
    # Proxy > Checker
    PROXY_CHECKER_PATH                     = f'{PROXY_PATH}>Checker'
    PROXY_CHECKER_MAIN_THREADS             = f'{PROXY_CHECKER_PATH}>Main Threads'
    PROXY_CHECKER_MAXIMUM_WAIT_RESPONSE    = f'{PROXY_CHECKER_PATH}>Maximum Wait Response'
    PROXY_CHECKER_SAVE_GOOD_IN_CUSTOM_FILE = f'{PROXY_CHECKER_PATH}>Save Good In Custom File'
    PROXY_CHECKER_SAVE_WITHOUT_PROTOCOL    = f'{PROXY_CHECKER_PATH}>Save Without Protocol'
    
    # Roblox
    ROBLOX_PATH = 'Roblox'
    
    # Roblox > General
    ROBLOX_GENERAL_PATH = f'{ROBLOX_PATH}>General'
    
    # Roblox > General > Proxy
    ROBLOX_GENERAL_PROXY_PATH                           = f'{ROBLOX_GENERAL_PATH}>Proxy'
    ROBLOX_GENERAL_PROXY_USE_PROXY                      = f'{ROBLOX_GENERAL_PROXY_PATH}>Use Proxy'
    ROBLOX_GENERAL_PROXY_AUTO_PROTOCOL_IF_NOT_SPECIFIED = f'{ROBLOX_GENERAL_PROXY_PATH}>Auto Protocol If Not Specified'
    
    # Roblox > Cookie Sorter
    ROBLOX_COOKIE_SORTER_PATH            = f'{ROBLOX_PATH}>Cookie Sorter'
    ROBLOX_COOKIE_SORTER_OUTPUT_FILENAME = f'{ROBLOX_COOKIE_SORTER_PATH}>Output Filename'
    ROBLOX_COOKIE_SORTER_THREADS         = f'{ROBLOX_COOKIE_SORTER_PATH}>Threads'
    
    # Misc
    MISC_PATH        = 'Misc'
    MISC_DISCORD_RPC = f'{MISC_PATH}>Discord RPC'
