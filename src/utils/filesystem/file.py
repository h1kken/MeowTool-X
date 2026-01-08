import mmap
import shutil
import zipfile
from pathlib import Path
from typing import Collection, Optional, Any
from src.utils.consts import FILENAME_SPECIAL_CHARS, START_PATHS
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
    for path, kind in START_PATHS:
        match kind:
            case 'dir':
                create_folder(path, exist_ok=False)
            case 'file':
                create_folder(path.parent, exist_ok=False)
                create_file(path, exist_ok=False)


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
        raise NotADirectoryError
    if not path.exists():
        raise FileExistsError
    
    return [dir.name for dir in path.iterdir() if dir.is_file() or not only_files]


def count_lines_in_file(path: Path) -> int:
    with open(path, 'rb') as f:
        if f.seek(0, 2) == 0:
            return 0
        f.seek(0)
        
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            count = 0
            pos = 0

            while True:
                pos = mm.find(b'\n', pos)
                if pos == -1:
                    break
                count += 1
                pos += 1
                
        if count > 0:
            f.seek(-1, 2)
            if f.read(1) != b'\n':
                count += 1

    return count


def validate_filename(filename: str, *, black_list: Collection[str] = [], default: str = 'output') -> str:
    if (
        not filename
        or filename in black_list
        or any(char in filename for char in FILENAME_SPECIAL_CHARS)
    ):
        return default
    return filename
