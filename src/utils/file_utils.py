from typing import Optional, Any
import zipfile
from pathlib import Path
from src.utils.logger import logger

def create_start_folders_and_files() -> None:
    PATHS = [
        ('Proxy', 'Checker', 'proxies.txt'),
        ('Roblox', 'proxies.txt'),
        ('Roblox', 'Cookie Sorter'),
        ('Roblox', 'Cookie Checker', 'cookies.txt'),
        # ('Roblox', 'LogPass Checker', 'LogPasses.txt'),
        # ('Roblox', 'Game Checker', 'cookies.txt'),
        ('Roblox', 'Cookie Refresher', 'Mass Mode', 'cookies.txt'),
        ('Roblox', 'Transaction Analysis', 'cookies.txt'),
        # ('Roblox', 'Time Booster', 'cookies.txt'),
        # ('Roblox', 'Robux Transfer', 'cookies.txt)
    ]

    for args in PATHS:
        path = Path(*args)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix and not path.exists():
            path.touch(exist_ok=True)

def get_nested(data: dict, key: str, *, sep: str = '>', default: Optional[Any] = None):
    keys = key.split(sep)
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def set_nested(data: dict, key: str, value: Any, *, sep: str = '>') -> None:
    keys = key.split(sep)
    current = data
    for key in keys[:-1]:
        if not isinstance(current[key], dict) or key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_files_from_folder(*path_args: str, only_files: bool = True) -> list[str]:
    path = Path(*path_args)
    if not (path.is_dir() and path.exists()):
        return []
    return [dir.name for dir in path.iterdir() if dir.is_file() or not only_files]

def amount_of_lines(*path_args: str) -> str:
    path = Path(*path_args)
    try:
        with open(path, 'r', encoding='UTF-8', errors='ignore') as file:
            amount = sum(1 for _ in file)
        return f'{amount} line{'s' if amount != 1 else ''}'
    except FileNotFoundError:
        return '0 lines'
    
async def make_archive(*path_args: str) -> None: 
    path = Path(*path_args)
    if path.exists():
        path = path.parent / 'archives' / path.name
        path.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        zipf.write(file_path, file_path.relative_to(path))
        except Exception as e:
            logger.exception(f'< [MAKE_ARCHIVE] > {...}: {e}')