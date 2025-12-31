import shutil
from typing import Collection, Optional, Any
import zipfile
from pathlib import Path
from src.utils.consts import FILENAME_CHARS, START_PATHS
from src.utils.decorators import log_action


@log_action('create folder')
def create_folder(path: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
    path.mkdir(parents=parents, exist_ok=exist_ok)

@log_action('delete folder') 
def delete_folder(path: Path, *, ignore_errors: bool = True) -> None:
    shutil.rmtree(path, ignore_errors=ignore_errors)

@log_action('create file')
def create_file(path: Path, *, exist_ok: bool = True) -> None:
    path.touch(exist_ok=exist_ok)

@log_action('create clean file')
def create_clean_file(path: Path, *, overwrite: bool = True) -> None:
    if overwrite or not path.exists():
        open(path, 'w').close()

@log_action('copy file')
def copy_file(src: Path, dest: Path, *, overwrite: bool = True) -> None:
    if overwrite or not dest.exists():
        shutil.copy(src, dest)

@log_action('delete file')
def delete_file(path: Path, *, missing_ok: bool = True) -> None:
    path.unlink(missing_ok=missing_ok)
    
@log_action('create archive')
def create_archive(path: Path, *, overwrite: bool = True) -> None:
    if not (overwrite or path.exists()):
        return
    
    path = path.parent / 'archives' / path.name
    path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in path.rglob('*'):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(path))
    
def create_start_folders_and_files() -> None:
    for path in START_PATHS:
        create_folder(path.parent)
        if path.suffix:
            create_file(path)

def get_safe(data: dict, key: str, *, sep: str = '>', default: Optional[Any] = None):
    keys = key.split(sep)
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def set_safe(data: dict, key: str, value: Any, *, sep: str = '>') -> None:
    keys = key.split(sep)
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_files_from_folder(path: Path, *, only_files: bool = True) -> list[str]:
    if not path.is_dir():
        raise NotADirectoryError(f'Path is not a directory: {path}')
    if not path.exists():
        return []
    
    return [dir.name for dir in path.iterdir() if dir.is_file() or not only_files]

def amount_of_lines(path: Path) -> str:
    try:
        with open(path, 'r', encoding='UTF-8', errors='ignore') as file:
            amount = sum(1 for _ in file)
        return f'{amount} line{'s' if amount != 1 else ''}'
    except Exception:
        return '0 lines'

def validate_filename(path: Path, black_list: Collection[str], default: str) -> Path:
    if (
        not path.stem or
        any(name == path.stem for name in black_list) or
        any(char in path.stem for char in FILENAME_CHARS)
    ):
        return path.parent / default
    return path