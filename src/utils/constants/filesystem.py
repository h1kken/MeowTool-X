from pathlib import Path

PROGRAM_NAME_SPECIAL_CHARS = {'<', '>', '|', '^', '&'}
FILENAME_SPECIAL_CHARS = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}

START_PATHS = [
    (Path('Proxy', 'Checker', 'proxies.txt'), 'file'),
    (Path('Roblox', 'proxies.txt'), 'file'),
    (Path('Roblox', 'Cookie Sorter'), 'dir'),
    (Path('Roblox', 'Cookie Checker', 'cookies.txt'), 'file'),
    # (Path('Roblox', 'LogPass Checker', 'LogPasses.txt'), 'file'),
    # (Path('Roblox', 'Game Checker', 'cookies.txt'), 'file'),
    (Path('Roblox', 'Cookie Refresher', 'Mass Mode', 'cookies.txt'), 'file'),
    (Path('Roblox', 'Transaction Analysis', 'cookies.txt'), 'file'),
    # (Path('Roblox', 'Time Booster', 'cookies.txt'), 'file'),
    # (Path('Roblox', 'Robux Transfer', 'cookies.txt'), 'file'),
]


__all__ = [name for name in globals() if name.isupper()]
