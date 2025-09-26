from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path

def create_needed_folders_and_files() -> None:
    PATHS = [
        ('Proxy', 'Checker', 'proxies.txt'),
        ('Roblox', 'proxies.txt'),
        ('Roblox', 'Cookie Sorter'),
        ('Roblox', 'Cookie Checker', 'cookies.txt'),
        # ('Roblox', 'LogPass Checker', 'LogPasses.txt'),
        # ('Roblox', 'Game Checker', 'cookies.txt'),
        ('Roblox', 'Cookie Refresher', 'Mass Mode', 'cookies.txt'),
        ('Roblox', 'Transaction Analysis', 'cookies.txt'),
        ('Roblox', 'Time Booster', 'cookies.txt'),
        # ('Roblox', 'Robux Transfer', 'cookies.txt)
    ]

    for args in PATHS:
        path = Path(*args)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix and not path.exists():
            path.touch(exist_ok=True)

def get_nested(data: dict, key: str, *, sep='.', default=None):
    keys = key.split(sep)
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def set_nested(data: dict, key: str, value, *, sep='.') -> None:
    keys = key.split(sep)
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_files_from_folder(*path_args: str, only_files: bool = True) -> list[str]:
    PATH = Path(*path_args)
    
    if not (PATH.exists() or PATH.is_dir()):
        return []

    return [p.name for p in PATH.iterdir() if p.is_file() or not only_files]

def amount_of_lines(*path_args: str) -> str:
    PATH = Path(*path_args)
    try:
        with open(PATH, 'r', encoding='UTF-8', errors='ignore') as file:
            amount = sum(1 for _ in file)
        return f'{amount} line{'s' if amount != 1 else ''}'
    except FileNotFoundError:
        return '0 lines'
    
async def make_archive(*path_args: str) -> None:
    path = Path(*path_args)
    if path.exists():
        path.mkdir(path.parent / 'archives', parents=True, exist_ok=True)
        path = path.parent / 'archives' / path.name
        with ZipFile(path, 'w', ZIP_DEFLATED) as zipf:
            path_length = len(path) + 1
            for root, _, files in path.walk():
                for file in files:
                    file_path = Path(root, file)
                    arcname = file_path[path_length:]
                    zipf.write(file_path, arcname)