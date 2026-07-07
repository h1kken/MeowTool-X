from __future__ import annotations

from pathlib import Path

PROGRAM_NAME_SPECIAL_CHARS = {'<', '>', '|', '^', '&'}
FILENAME_SPECIAL_CHARS = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}

START_DIR_PATHS = [
    Path('Roblox', 'Cookie Sorter'),
]

START_FILE_PATHS = [
    Path('Proxy', 'Checker', 'proxies.txt'),
    Path('Roblox', 'proxies.txt'),
    Path('Roblox', 'Cookie Checker', 'cookies.txt'),
    Path('Roblox', 'LogPass Checker', 'LogPasses.txt'),
    Path('Roblox', 'Game Checker', 'cookies.txt'),
    Path('Roblox', 'Cookie Refresher', 'cookies.txt'),
    Path('Roblox', 'Transaction Analysis', 'cookies.txt'),
    Path('Roblox', 'Time Booster', 'cookies.txt'),
    Path('Roblox', 'Robux Transfer', 'cookies.txt'),
]


__all__ = (
    'PROGRAM_NAME_SPECIAL_CHARS',
    'FILENAME_SPECIAL_CHARS',
    'START_DIR_PATHS',
    'START_FILE_PATHS',
)
